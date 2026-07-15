from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _atomic_write(path: Path, writer: Callable[[TextIO], None]) -> None:
    """Write a complete replacement in the destination directory, then rename it."""
    ensure_dir(path.parent)
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            writer(f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def write_json(path: Path, data: Any) -> None:
    def write(f: TextIO) -> None:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    _atomic_write(path, write)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    def write(f: TextIO) -> None:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    _atomic_write(path, write)


def slug_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]
