from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


DEFAULT_TRUSTED_CLIENTS_FILE = Path("trusted_clients.json")


def hash_uuid(uuid: str) -> str:
    return hashlib.sha256(uuid.encode("utf-8")).hexdigest()


def load_trusted_clients(path: str | Path = DEFAULT_TRUSTED_CLIENTS_FILE) -> dict[str, str]:
    trusted_path = Path(path)
    if not trusted_path.exists():
        return {}

    try:
        with trusted_path.open("r", encoding="utf-8") as trusted_file:
            data = json.load(trusted_file)
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    return {
        str(name): str(client_hash)
        for name, client_hash in data.items()
        if name and client_hash
    }


def save_trusted_clients(
    trusted_clients: Mapping[str, str],
    path: str | Path = DEFAULT_TRUSTED_CLIENTS_FILE,
) -> None:
    trusted_path = Path(path)
    trusted_path.parent.mkdir(parents=True, exist_ok=True)

    cleaned = {
        str(name): str(client_hash)
        for name, client_hash in trusted_clients.items()
        if name and client_hash
    }

    temp_path = trusted_path.with_name(f"{trusted_path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as trusted_file:
        json.dump(cleaned, trusted_file, indent=4, sort_keys=True)
        trusted_file.write("\n")

    temp_path.replace(trusted_path)
