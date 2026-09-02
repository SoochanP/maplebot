from __future__ import annotations

import re

from app.commands.base import CommandHandler
from app.core.exceptions import InvalidCommandError
from app.data.hexa_costs import calculate_hexa_cost_summary
from app.models.command import ParsedCommand
from app.models.hexa_cost import HexaCostSummary


class HexaCostCommand(CommandHandler):
    command_name = "\ud5e5\uc0ac\ube44\uc6a9"
    requires_character_name = False
    requires_argument_text = True
    usage_example = "!\ud5e5\uc0ac\ube44\uc6a9 1->30"
    missing_argument_message = "\ub808\ubca8 \uad6c\uac04\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694. \uc608\uc2dc: !\ud5e5\uc0ac\ube44\uc6a9 1->30"

    _LEVEL_RANGE_PATTERN = re.compile(r"^(?P<current>\d+)\s*(?:->|\s+)\s*(?P<target>\d+)$")
    _INVALID_RANGE_MESSAGE = "\ub808\ubca8 \uad6c\uac04 \ud615\uc2dd\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc608\uc2dc: !\ud5e5\uc0ac\ube44\uc6a9 1->30"

    async def handle(self, command: ParsedCommand) -> str:
        argument_text = self.require_argument_text(command)
        current_level, target_level = self._parse_level_range(argument_text)
        summary = calculate_hexa_cost_summary(current_level, target_level)
        return self._format_response(summary)

    def _parse_level_range(self, argument_text: str) -> tuple[int, int]:
        match = self._LEVEL_RANGE_PATTERN.fullmatch(argument_text)
        if match is None:
            raise InvalidCommandError(self._INVALID_RANGE_MESSAGE)

        current_level = int(match.group("current"))
        target_level = int(match.group("target"))
        if current_level < 1 or target_level > 30 or current_level >= target_level:
            raise InvalidCommandError(self._INVALID_RANGE_MESSAGE)
        return current_level, target_level

    @staticmethod
    def _format_response(summary: HexaCostSummary) -> str:
        sections = [f"[HEXA \uac15\ud654 \ube44\uc6a9 {summary.current_level} \u2192 {summary.target_level}]"]

        for profile in summary.profiles:
            sections.append(
                "\n".join(
                    [
                        profile.profile_name,
                        f"\uc194 \uc5d0\ub974\ub2e4: {profile.sol_erda:,}\uac1c (\uae30\uc6b4 {profile.energy:,})",
                        f"\uc870\uac01: {profile.fragments:,}\uac1c",
                    ]
                )
            )

        return "\n\n".join(sections)
