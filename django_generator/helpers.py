import logging
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from datetime import datetime

LOG_FILE = Path.home() / ".django_generator.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def log(cb: Optional[Callable], msg: str, level=logging.INFO):
    """Unified logging helper (writes to file + callback + stdout)."""
    logging.log(level, msg)
    if cb:
        try:
            cb(msg)
        except Exception:
            pass
    else:
        print(msg)


def run_command(cmd: List[str], cwd: Optional[str] = None, cb: Optional[Callable] = None) -> str:
    """Run subprocess command safely and log output.

    Note: shell=True is avoided unless on Windows where PATH resolution is trickier.
    """
    try:
        cmd = [str(c) for c in cmd]
        shell_flag = os.name == "nt"
        log(cb, f"→ {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=shell_flag)

        out = proc.stdout or ""
        err = proc.stderr or ""
        for line in out.splitlines():
            if line.strip():
                log(cb, f"   {line}")

        if proc.returncode != 0:
            msg = err.strip() or out.strip()
            log(cb, f"❌ Command failed: {msg}")
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=out, stderr=err)

        return out.strip()
    except Exception as e:
        log(cb, f"❌ Error running {' '.join(cmd)}: {e}")
        raise
