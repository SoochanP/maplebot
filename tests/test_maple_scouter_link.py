from __future__ import annotations

from app.services.maple_scouter_link import MapleScouterLinkBuilder


def test_build_generates_maple_scouter_link_for_changkil() -> None:
    builder = MapleScouterLinkBuilder()

    url = builder.build("창킬")

    assert url == "https://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"


def test_build_generates_maple_scouter_link_for_another_korean_name() -> None:
    builder = MapleScouterLinkBuilder()

    url = builder.build("햇살렌")

    assert url == "https://maplescouter.com/ko/info?name=%ED%96%87%EC%82%B4%EB%A0%8C"


def test_build_url_encodes_reserved_characters() -> None:
    builder = MapleScouterLinkBuilder()

    url = builder.build("A+B")

    assert url == "https://maplescouter.com/ko/info?name=A%2BB"


def test_build_trims_surrounding_whitespace() -> None:
    builder = MapleScouterLinkBuilder()

    url = builder.build("  김메이플  ")

    assert url == "https://maplescouter.com/ko/info?name=%EA%B9%80%EB%A9%94%EC%9D%B4%ED%94%8C"
