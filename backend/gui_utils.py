# -*- coding: utf-8 -*-
"""
gui_utils.py - Shared utilities for GUI-aware output.

Provides a consistent way for all backend scripts to emit JSON messages
to the Electron GUI, avoiding code duplication across scripts.
"""

from __future__ import annotations

import json


def emit(gui_mode: bool, msg: dict) -> None:
    """Send a JSON message to stdout for the Electron GUI.

    When gui_mode is False, this is a no-op so callers don't need
    to guard every call.

    Args:
        gui_mode: Whether to output JSON (True) or do nothing (False).
        msg: Dictionary to serialize as a JSON line.
    """
    if gui_mode:
        print(json.dumps(msg, ensure_ascii=False), flush=True)
