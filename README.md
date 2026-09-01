# MapleBot

MapleBot is a maintainable command-based MapleStory chatbot backend focused on readable architecture, clean boundaries, and easy future expansion. KakaoTalk integration is currently limited to webhook application wiring and first-connection safety checks.

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

- `MAPLEBOT_KAKAO_SKILL_TOKEN`: optional webhook secret checked against `X-MapleBot-Token`
- `MAPLEBOT_KAKAO_REQUEST_TIMEOUT_SECONDS`: overall Kakao webhook execution limit, default `4.5`
- `MAPLEBOT_HTTP_REQUEST_TIMEOUT_SECONDS`: shared outbound request timeout, default `3.0`
- `MAPLEBOT_HTTP_CONNECT_TIMEOUT_SECONDS`: shared outbound connect timeout, default `1.0`

Behavior:

- If `MAPLEBOT_KAKAO_SKILL_TOKEN` is configured, `POST /kakao/webhook` requires a matching `X-MapleBot-Token` header.
- If `MAPLEBOT_KAKAO_SKILL_TOKEN` is not configured, the webhook remains open for local development and tests.
- `GET /health` is always public.

## Run Tests

```bash
pytest
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
MapleBot > !경험치 히스토리 창킬

[창킬 경험치 히스토리]

01/08  Lv.289  31.845%
01/09  Lv.289  33.576%  (+1.731%)
01/10  Lv.289  35.527%  (+1.951%)
01/11  Lv.289  40.050%  (+4.523%)
01/12  Lv.289  41.334%  (+1.284%)

최근 5개 기록 변화: +13,824,848,783,387 EXP (+9.489%)
```

## Run FastAPI

```bash
uvicorn app.main:app --reload
```

Health check:

```text
GET /health
```

Kakao webhook:

```text
POST /kakao/webhook
```

Example request:

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

Example response:

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

## Current Supported Commands

- `!환산 캐릭터명`
- `!경험치 히스토리 캐릭터명`

## Architecture Overview

- `CommandRouter`: validates input, matches the longest registered command name, routes to the correct handler, and can safely expose a matched command name for logging.
- `ConvertedStatCommand`: receives the character name, asks the link builder for a URL, and formats the user-facing response.
- `ExperienceHistoryCommand`: receives the character name, selects the latest five snapshots by timestamp, displays them chronologically, and formats only mathematically safe gain indicators.
- `Kakao webhook`: validates the minimal Kakao request payload, authenticates the optional secret header, extracts `userRequest.utterance`, dispatches through `CommandRouter`, enforces a short request budget, and formats a `simpleText` response.
- `CLI` and Kakao webhook share the same command pipeline and do not duplicate command logic.
- `MapleScouterLinkBuilder`: owns MapleScouter URL rules and URL encoding.
- `MapleHistoryCrawler`: owns MapleHiStory-specific `/ajax/*` requests and response parsing.
- `HttpClientManager`: owns the reusable `httpx.AsyncClient` lifecycle for crawler-based commands.
- `ApplicationSettings`: owns environment-based webhook/auth/timeout configuration.
- `Pydantic` models: used for typed command payloads, typed experience history results, typed Kakao webhook payloads, and settings validation.

## Add Another Command

1. Create a new handler in `app/commands/`.
2. Add any typed request or result models in `app/models/` when the command needs them.
3. Inject the handler dependency in `build_application_services()` inside `app/bootstrap.py`.
4. Add router tests and handler tests.

## Add Another Crawler

1. Create a crawler module in `app/crawlers/`.
2. Keep site URLs, headers, selectors, and parsing logic inside that crawler.
3. Return typed models instead of raw dictionaries.
4. Inject the crawler into the command handler through the constructor.
5. Add parser tests and mock-transport tests for networking and error handling.

## Notes

- `!환산` does not crawl MapleScouter and does not call MapleScouter APIs.
- `!경험치 히스토리` uses MapleHiStory public site endpoints under `/ajax/*` and does not require browser automation in the current implementation.
- `POST /kakao/webhook` only authenticates the optional skill token, parses Kakao input, calls the existing command pipeline, and formats Kakao output.
- The Kakao webhook logs concise request outcome data such as command name when derivable, duration, success or failure, and expected application error category.
- `httpx` remains the shared HTTP client for crawler-based commands.
- `selectolax` stays in the stack for future HTML parsing needs, but it is not required for the current commands.
- KakaoTalk channel registration, deployment, database, Redis, AI, MCP, and Playwright are intentionally excluded from this phase.
