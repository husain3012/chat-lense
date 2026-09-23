import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
MAX_EXPANDED = int(os.getenv("MAX_EXPANDED_MB", "500")) * 1024 * 1024
MAX_FILES = 10000
ACCEPTED = {".txt", ".json", ".db", ".sqlite", ".sqlite3", ".zip"}


def prepare(path: Path) -> Path:
    if path.suffix.lower() != ".zip":
        return path
    destination = path.parent / "extracted"
    destination.mkdir()
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_EXPANDED:
            raise ValueError("Archive exceeds expanded size or file count limit")
        for info in infos:
            name = PurePosixPath(info.filename.replace("\\", "/"))
            if (
                name.is_absolute()
                or ".." in name.parts
                or ":" in info.filename
                or stat.S_ISLNK(info.external_attr >> 16)
            ):
                raise ValueError("Unsafe archive path or symbolic link")
            if info.file_size > MAX_EXPANDED or (
                info.file_size > 1024 * 1024
                and info.file_size / max(1, info.compress_size) > 200
            ):
                raise ValueError("Suspicious archive compression ratio")
            if info.flag_bits & 1:
                raise ValueError("Encrypted ZIP archives are not supported")
        written = 0
        for info in infos:
            if info.is_dir() or Path(info.filename).suffix.lower() not in ACCEPTED - {
                ".zip"
            }:
                continue  # Media bytes are not extracted or served in Phase 1.
            target = destination.joinpath(
                *PurePosixPath(info.filename.replace("\\", "/")).parts
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as out:
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > MAX_EXPANDED:
                        raise ValueError("Expanded archive is too large")
                    out.write(chunk)
    return destination
