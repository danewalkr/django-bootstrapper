#!/usr/bin/env python3
"""
Django Project Generator (Refactored, Single-File Edition)

Creates a Django project with:
- optional .venv
- installs Django
- creates project + apps
- creates templates/static with base/home/app_index fallbacks
- patches settings.py to include templates/static and apps
- wires app urls into project urls.py (home route renders template)
- writes requirements.txt
- optional git init

Single-file, GUI kept similar to original.
"""
import os
import sys
import subprocess
import threading
import textwrap
import venv
from pathlib import Path
from typing import Optional, Callable, List
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from datetime import datetime
from tkinter.scrolledtext import ScrolledText

__version__ = "1.0.0"

# --- Logging setup ---
LOG_FILE = Path.home() / ".django_generator.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info(f"--- Django Generator started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

# -------------------------
# Helpers
# -------------------------
def run_command(cmd: List[str], cwd: Optional[str] = None, cb: Optional[Callable] = None) -> str:
    """Run subprocess command safely (cross-platform) and log output incrementally."""
    try:
        cmd = [str(c) for c in cmd]
        shell_flag = os.name == "nt"  # needed for Windows PATH resolution
        log(cb, f"→ {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=shell_flag)

        if proc.stdout:
            for line in proc.stdout.strip().splitlines():
                log(cb, f"   {line}")

        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            log(cb, f"❌ Aborting — command failed: {err}")
            raise SystemExit(1)

        return proc.stdout.strip()

    except Exception as e:
        log(cb, f"❌ Error running {' '.join(cmd)}: {e}")
        raise

def log(cb: Optional[Callable], msg: str, level=logging.INFO):
    """Unified logging helper (writes to file + GUI + console)."""
    logging.log(level, msg)

    # Send to GUI callback if available
    if cb:
        cb(msg)
    else:
        print(msg)

"""Compatibility shim that exposes the new modular package API.

This file keeps the previous top-level module name (`django_generator.py`) so older
imports continue to work. It re-exports the package's create_project and GUI class
and provides the same simple CLI (launches the GUI when run directly).
"""

from pathlib import Path

# Re-export core API and GUI from the package
import importlib

pkg = importlib.import_module("django_generator")
create_project = getattr(pkg, "create_project")
DjangoGeneratorApp = getattr(pkg, "DjangoGeneratorApp")

__all__ = ["create_project", "DjangoGeneratorApp"]


if __name__ == "__main__":
    app = DjangoGeneratorApp()
    app.mainloop()