# MapleBot

MapleBot is a maintainable command-based MapleStory chatbot backend. It provides a shared command pipeline for a local CLI, the official Kakao chatbot webhook, and an Android bridge endpoint.

## Requirements

- Python 3.12+
- pip

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Configuration

Environment variables:

- `MAPLEBOT_NEXON_API_KEY`: required for NEXON-backed commands, sent as `x-nxopen-api-key`
- `MAPLEBOT_KAKAO_SKILL_TOKEN`: optional official Kakao webhook secret checked against `X-MapleBot-Token`
- `MAPLEBOT_BRIDGE_TOKEN`: optional bridge secret checked against `X-MapleBot-Bridge-Token`
- `MAPLEBOT_KAKAO_REQUEST_TIMEOUT_SECONDS`: Kakao skill response budget, default `4.5`
- `MAPLEBOT_COMMAND_EXECUTION_TIMEOUT_SECONDS`: shared bridge and Kakao command execution limit, default `15.0`
- `MAPLEBOT_HTTP_REQUEST_TIMEOUT_SECONDS`: shared outbound request timeout, default `8.0`
- `MAPLEBOT_HTTP_CONNECT_TIMEOUT_SECONDS`: shared outbound connect timeout, default `2.0`

Behavior:

- If `MAPLEBOT_NEXON_API_KEY` is missing, `!헥사`, `!유니온`, `!랭킹`, `!공지`, and `!경험치 히스토리` return a clear configuration error. `!환산` continues to work because it does not call NEXON.
- If `MAPLEBOT_KAKAO_SKILL_TOKEN` is configured, `POST /kakao/webhook` requires a matching `X-MapleBot-Token` header.
- If `MAPLEBOT_BRIDGE_TOKEN` is configured, `POST /bridge/message` requires a matching `X-MapleBot-Bridge-Token` header.
- If either webhook token is not configured, that endpoint remains open for local development and tests.
- `GET /health` is always public.
- `GET /health/ready` is always public and returns a lightweight readiness response for external wake-up probes.

## Run Tests

```bash
.venv\Scripts\python.exe -m pytest
```

## Run The CLI

```bash
python -m app.cli
```

Examples:

```text
MapleBot > !환산 창킬

[창킬 환산주스탯]

https://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC
```

```text
MapleBot > !공지

[메이플스토리 최신 공지]

1. 09/02 점검 안내
2. 09/01 이벤트 안내
3. ...
```

## Run FastAPI

```bash
uvicorn app.main:app --reload
```

Available endpoints:

- `GET /health`
- `GET /health/ready`
- `POST /kakao/webhook`
- `POST /bridge/message`

Example official Kakao request:

```http
POST /kakao/webhook
X-MapleBot-Token: your-skill-token
Content-Type: application/json
```

```json
{
  "userRequest": {
    "utterance": "!환산 창킬"
  }
}
```

Example official Kakao response:

```json
{
  "version": "2.0",
  "template": {
    "outputs": [
      {
        "simpleText": {
          "text": "[창킬 환산주스탯]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
        }
      }
    ]
  }
}
```

Example bridge request:

```http
POST /bridge/message
X-MapleBot-Bridge-Token: your-bridge-token
Content-Type: application/json
```

```json
{
  "room": "메이플 단톡방",
  "sender": "사용자",
  "message": "!환산 창킬"
}
```

Example bridge response:

```json
{
  "reply": "[창킬 환산주스탯]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
}
```

## MessageBotR Wake-Up Integration

- This repository does not contain the real MessageBotR operating source.
- `GET /health/ready` returns `204 No Content` with an empty body and may be used as a lightweight wake trigger before a single retry.
- Recommended client policy:
  - first try `POST /bridge/message`
  - retry only for network-level failures such as `SocketException`, `SocketTimeoutException`, connection abort/reset, or no HTTP response received
  - on a retryable network failure, call `GET /health/ready`, wait `2500ms`, then retry the original `POST /bridge/message` exactly once
  - do not retry when an actual HTTP response was received, including `400`, `404`, `422`, `500`, `502`, or `503`

Minimal MessageBotR example to apply in the existing shared HTTP request function:

```javascript
function requestMapleBot(url, body) {
    try {
        return executeRequest(url, body);
    } catch (error) {
        if (!isRetryableNetworkError(error)) {
            throw error;
        }

        wakeMapleBotServer();
        java.lang.Thread.sleep(2500);
        return executeRequest(url, body);
    }
}

function wakeMapleBotServer() {
    try {
        org.jsoup.Jsoup.connect(SERVER_BASE_URL + "/health/ready")
            .ignoreContentType(true)
            .ignoreHttpErrors(true)
            .timeout(3000)
            .method(org.jsoup.Connection.Method.GET)
            .execute();
    } catch (error) {
        // Cold start may still begin even if the wake request times out.
    }
}

function isRetryableNetworkError(error) {
    var message = String(error);

    return message.indexOf("SocketException") >= 0 ||
        message.indexOf("SocketTimeoutException") >= 0 ||
        message.indexOf("connection abort") >= 0 ||
        message.indexOf("Connection reset") >= 0 ||
        message.indexOf("timed out") >= 0;
}
```

Manual verification checklist:

- healthy server: first `POST /bridge/message` succeeds, no wake request, no retry
- `Software caused connection abort`: wake with `GET /health/ready`, wait `2500ms`, retry the original `POST /bridge/message` once
- retry failure: stop after the second request and surface the existing error handling
- HTTP `500`: do not wake and do not retry because the server already responded

## Current Supported Commands

- `!환산 캐릭터명`
- `!헥사 캐릭터명`
- `!유니온 캐릭터명`
- `!랭킹 캐릭터명`
- `!공지`
- `!경험치 히스토리 캐릭터명`

## Architecture Overview

- `CommandRouter`: validates input, matches the longest registered command name, and dispatches to the correct handler.
- `ConvertedStatCommand`: keeps `!환산` as a link-only command through `MapleScouterLinkBuilder`.
- `HexaCommand`, `UnionCommand`, `RankingCommand`, `NoticeCommand`, `ExperienceHistoryCommand`: format user-facing text from typed result models.
- `NexonMapleClient`: owns OCID lookup, NEXON Open API request construction, authentication header injection, date-aware history queries, and provider error translation.
- `HttpClientManager`: owns the shared `httpx.AsyncClient` lifecycle for CLI and FastAPI.
- `Kakao webhook` and `bridge endpoint`: authenticate, parse the request, call `CommandRouter`, and format transport-specific responses without command-specific logic.
- `ApplicationSettings`: owns environment-based tokens, timeouts, and the NEXON API key.

## NEXON Endpoints Used

- `GET /maplestory/v1/id`
- `GET /maplestory/v1/character/basic`
- `GET /maplestory/v1/character/hexamatrix`
- `GET /maplestory/v1/character/hexamatrix-stat`
- `GET /maplestory/v1/user/union`
- `GET /maplestory/v1/user/union-artifact`
- `GET /maplestory/v1/user/union-champion`
- `GET /maplestory/v1/ranking/overall`
- `GET /maplestory/v1/notice`

## Add Another Command

1. Create a new handler in `app/commands/`.
2. Add or reuse typed models in `app/models/`.
3. Extend `NexonMapleClient` or another provider client only when external data access is needed.
4. Register the handler in `build_application_services()` inside `app/bootstrap.py`.
5. Add router, handler, and provider tests.

## Add Another Crawler Or Provider Client

1. Create a provider module under `app/clients/` or `app/crawlers/` depending on whether the source is a structured API or HTML site.
2. Keep URLs, headers, selectors, and provider-specific parsing inside that module.
3. Return typed models instead of raw dictionaries.
4. Inject the provider dependency into the command handler through the constructor.
5. Add mock-transport tests for networking and parser behavior.

## Notes

- `!환산` does not call NEXON and remains a MapleScouter link builder command.
- `!경험치 히스토리` now uses NEXON `character/basic` historical date queries instead of MapleHiStory.
- Ranking data follows NEXON's documented freshness rules and falls back across the latest two KST dates when needed.
- The HTTP integrations log concise request outcome data such as command name when derivable, duration, success or failure, and expected application error category.
- No database, Redis, AI, MCP, or Playwright is included in this phase.
- Render deployment needs `MAPLEBOT_NEXON_API_KEY=<secret>` before the new NEXON-backed commands can work in production.
