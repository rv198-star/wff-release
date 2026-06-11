#!/usr/bin/env python3
"""Load runtime data assets declared by script modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_script_text_asset(module_file: str | Path, asset_name: str) -> str:
    return (Path(module_file).resolve().parent / "data" / asset_name).read_text(encoding="utf-8")


def load_script_json_asset(module_file: str | Path, asset_name: str) -> Any:
    return json.loads(load_script_text_asset(module_file, asset_name))
