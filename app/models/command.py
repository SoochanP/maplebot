from pydantic import BaseModel, ConfigDict


class ParsedCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    raw_text: str
    command: str
    character_name: str
