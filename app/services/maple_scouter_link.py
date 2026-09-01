from __future__ import annotations

from urllib.parse import quote


class MapleScouterLinkBuilder:
    BASE_URL = "https://maplescouter.com/ko/info"

    def build(self, character_name: str) -> str:
        encoded_character_name = quote(character_name.strip(), safe="")
        return f"{self.BASE_URL}?name={encoded_character_name}"
