from __future__ import annotations

import asyncio

from app.bootstrap import build_application_services
from app.core.exceptions import MapleBotError


async def run_cli() -> None:
    services = build_application_services()
    await services.start()
    try:
        while True:
            try:
                raw_command = input("MapleBot > ").strip()
            except EOFError:
                print()
                break

            if not raw_command:
                continue

            if raw_command.lower() in {"exit", "quit"}:
                break

            try:
                response = await services.command_router.dispatch(raw_command)
            except MapleBotError as exc:
                response = exc.user_message

            print()
            print(response)
            print()
    finally:
        await services.close()


def main() -> None:
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()

