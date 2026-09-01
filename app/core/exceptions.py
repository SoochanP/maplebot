from __future__ import annotations


class MapleBotError(Exception):
    def __init__(self, user_message: str, *, details: str | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.details = details


class InvalidCommandError(MapleBotError):
    pass


class UnsupportedCommandError(InvalidCommandError):
    pass


class CrawlerError(MapleBotError):
    pass


class CharacterNotFoundError(CrawlerError):
    pass


class EmptyHistoryError(CrawlerError):
    pass


class ExternalSiteUnavailableError(CrawlerError):
    pass
