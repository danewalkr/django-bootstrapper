from pathlib import Path
import venv
import os
from typing import Optional

from .helpers import run_command, log


def create_virtualenv(base_dir: Path, cb=None) -> Path:
    venv_path = base_dir / ".venv"
    if not venv_path.exists():
        log(cb, f"⚙️ Creating virtual environment at {venv_path} ...")
        venv.EnvBuilder(with_pip=True).create(venv_path)
    else:
        log(cb, "ℹ️ .venv already exists, skipping creation.")
    python_exe = venv_path / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    return python_exe


def install_django(python_exe: Path, version: str, cb=None):
    log(cb, "📦 Installing/ensuring Django...")
    run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], cb=cb)
    if version:
        run_command([str(python_exe), "-m", "pip", "install", f"django=={version}"], cb=cb)
    else:
        run_command([str(python_exe), "-m", "pip", "install", "django"], cb=cb)
    log(cb, "✅ Django ready.")
