from __future__ import annotations

import asyncio

import pytest

from app.commands.hexa_cost import HexaCostCommand
from app.commands.router import CommandRouter
from app.core.exceptions import InvalidCommandError


EXPECTED_REPLY_1_TO_30 = (
    "[HEXA \uac15\ud654 \ube44\uc6a9 1 \u2192 30]\n\n"
    "6\ucc28 \uc2a4\ud0ac\n"
    "\uc194 \uc5d0\ub974\ub2e4: 145\uac1c (\uae30\uc6b4 145,000)\n"
    "\uc870\uac01: 4,400\uac1c\n\n"
    "3rd \uc2a4\ud0ac\n"
    "\uc194 \uc5d0\ub974\ub2e4: 110\uac1c (\uae30\uc6b4 110,000)\n"
    "\uc870\uac01: 3,302\uac1c\n\n"
    "\ub9c8\uc2a4\ud130\ub9ac\n"
    "\uc194 \uc5d0\ub974\ub2e4: 80\uac1c (\uae30\uc6b4 80,000)\n"
    "\uc870\uac01: 2,202\uac1c\n\n"
    "5\ucc28 \uac15\ud654\n"
    "\uc194 \uc5d0\ub974\ub2e4: 119\uac1c (\uae30\uc6b4 119,000)\n"
    "\uc870\uac01: 3,308\uac1c\n\n"
    "\uacf5\uc6a9\n"
    "\uc194 \uc5d0\ub974\ub2e4: 201\uac1c (\uae30\uc6b4 201,000)\n"
    "\uc870\uac01: 6,143\uac1c\n\n"
    "\uc9c1\uc5c5\uad70 \uacf5\uc6a9\n"
    "\uc194 \uc5d0\ub974\ub2e4: 133\uac1c (\uae30\uc6b4 133,000)\n"
    "\uc870\uac01: 3,945\uac1c"
)



def dispatch(raw_text: str) -> str:
    router = CommandRouter([HexaCostCommand()])
    return asyncio.run(router.dispatch(raw_text))


def test_hexa_cost_command_formats_expected_reply_for_1_to_30() -> None:
    assert dispatch("!\ud5e5\uc0ac\ube44\uc6a9 1->30") == EXPECTED_REPLY_1_TO_30


def test_hexa_cost_command_accepts_space_delimited_levels() -> None:
    assert dispatch("!\ud5e5\uc0ac\ube44\uc6a9 1 30") == EXPECTED_REPLY_1_TO_30


@pytest.mark.parametrize(
    "raw_text",
    [
        "!\ud5e5\uc0ac\ube44\uc6a9",
        "!\ud5e5\uc0ac\ube44\uc6a9 abc",
        "!\ud5e5\uc0ac\ube44\uc6a9 0->30",
        "!\ud5e5\uc0ac\ube44\uc6a9 30->30",
        "!\ud5e5\uc0ac\ube44\uc6a9 20->10",
        "!\ud5e5\uc0ac\ube44\uc6a9 1->31",
    ],
)
def test_hexa_cost_command_rejects_invalid_inputs(raw_text: str) -> None:
    with pytest.raises(InvalidCommandError):
        dispatch(raw_text)