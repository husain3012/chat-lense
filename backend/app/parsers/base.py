from abc import ABC, abstractmethod
from pathlib import Path
from app.schemas.chat import ParsedConversation


class ChatParser(ABC):
    @classmethod
    @abstractmethod
    def detect(cls, input_path: Path) -> float: ...

    @abstractmethod
    def parse(self, input_path: Path) -> list[ParsedConversation]: ...

    def validate(self, input_path: Path) -> list[str]:
        return [] if input_path.exists() else ["Input does not exist"]


def files(path: Path, suffix: str):
    return (
        sorted(path.rglob("*" + suffix))
        if path.is_dir()
        else ([path] if path.suffix.lower() == suffix else [])
    )
