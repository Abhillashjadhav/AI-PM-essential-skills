"""Dependency-free PEP 517 build backend for ContextPort."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path


NAME = "contextport"
VERSION = "0.1.0"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"
MODULES = (
    "chatgpt_adapter.py",
    "contextport.py",
    "reconciliation.py",
    "reconstruction.py",
    "review.py",
    "segregation.py",
    "sync.py",
)
DATA_GLOBS = ("schemas/*.json", "docs/*.md")
SOURCE_DATE = (2020, 1, 1, 0, 0, 0)


def _root() -> Path:
    return Path(__file__).resolve().parent


def _metadata() -> bytes:
    return (
        "Metadata-Version: 2.2\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Local-first, human-supervised conversational context portability\n"
        "Requires-Python: >=3.11\n"
        "Author-email: Abhillash Jadhav <abhilashjadhav@gmail.com>\n"
        "\n"
    ).encode()


def _wheel_files() -> list[tuple[str, bytes]]:
    root = _root()
    files = [(name, (root / name).read_bytes()) for name in MODULES]
    for pattern in DATA_GLOBS:
        for path in sorted(root.glob(pattern)):
            files.append((f"contextport_data/{path.relative_to(root).as_posix()}", path.read_bytes()))
    files.extend(
        [
            (f"{DIST_INFO}/METADATA", _metadata()),
            (f"{DIST_INFO}/WHEEL", b"Wheel-Version: 1.0\nGenerator: contextport_build 0.1\nRoot-Is-Purelib: true\nTag: py3-none-any\n"),
            (f"{DIST_INFO}/entry_points.txt", b"[console_scripts]\ncontextport = contextport:main\n"),
            (f"{DIST_INFO}/top_level.txt", b"contextport\n"),
        ]
    )
    return files


def _record_row(path: str, content: bytes) -> tuple[str, str, str]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
    return path, f"sha256={digest}", str(len(content))


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None) -> str:
    """Build a reproducible pure-Python wheel."""
    del config_settings, metadata_directory
    filename = f"{NAME}-{VERSION}-py3-none-any.whl"
    target = Path(wheel_directory) / filename
    files = _wheel_files()
    record_path = f"{DIST_INFO}/RECORD"
    record_buffer = io.StringIO(newline="")
    writer = csv.writer(record_buffer, lineterminator="\n")
    for path, content in files:
        writer.writerow(_record_row(path, content))
    writer.writerow((record_path, "", ""))
    files.append((record_path, record_buffer.getvalue().encode()))
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, content in sorted(files):
            info = zipfile.ZipInfo(path, SOURCE_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    return filename


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None) -> str:
    """Write standard wheel metadata without resolving dependencies."""
    del config_settings
    directory = Path(metadata_directory) / DIST_INFO
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "METADATA").write_bytes(_metadata())
    (directory / "WHEEL").write_text(
        "Wheel-Version: 1.0\nGenerator: contextport_build 0.1\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )
    return DIST_INFO


def build_sdist(sdist_directory, config_settings=None) -> str:
    """Build a reproducible source archive containing public runtime and build inputs."""
    del config_settings
    filename = f"{NAME}-{VERSION}.tar.gz"
    root = _root()
    included = ["README.md", "pyproject.toml", "contextport_build.py", *MODULES]
    for pattern in (*DATA_GLOBS, "tests/*.py"):
        included.extend(path.relative_to(root).as_posix() for path in sorted(root.glob(pattern)))
    with tarfile.open(Path(sdist_directory) / filename, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for relative in sorted(set(included)):
            content = (root / relative).read_bytes()
            info = tarfile.TarInfo(f"{NAME}-{VERSION}/{relative}")
            info.size = len(content)
            info.mtime = 0
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(content))
    return filename
