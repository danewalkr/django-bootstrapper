# Django Bootstrapper (Django Project Generator)

Lightweight tool to scaffold a Django project with optional virtualenv, apps, templates, and a modern dark-theme starter UI. Includes a small GUI and a CLI with a safe `--dry-run` mode so you can preview what will happen without making changes.

Below are instructions for using the tool.

---

## Quick features

- Create a Django project scaffold (project + optional apps)
- Optional `.venv` creation and Django installation
- Template/static generation with a modern dark theme and navbar that lists apps
- CLI and GUI frontends
- `--dry-run` mode to preview actions
- Sanitizer that inserts `{% load static %}` in generated templates

---

## Quick start (Windows PowerShell)

Prerequisites: Python 3.10+ (3.13 tested here), Git (optional)

Preview what will happen (dry-run — no changes):

```powershell
python .\cli.py --dry-run
```

Create a real project (will create `.venv` and install Django):

```powershell
python .\cli.py C:\path\to\outdir mysite --apps users accounts
```

Open the GUI:

```powershell
python .\cli.py --gui
```

Useful flags:

# Django Bootstrapper

Create a ready-to-run Django project in seconds — with optional virtualenv, apps, modern dark-themed templates, and both CLI and GUI frontends.

This README explains what the tool does, how to use it (CLI + GUI), and how to get started quickly.

---

## Features

- Create a Django project scaffold (project directory + optional apps)
- Optional `.venv` creation and automatic Django install
- Generates templates and static (modern dark theme with navbar)
- CLI and Tkinter GUI frontends
- Safe `--dry-run` mode to preview actions without making changes
- Sanitizer that injects `{% load static %}` and fixes common template whitespace issues

---

## Quick start

Requirements

- Python 3.10+ (3.13 tested here)
- (Optional) Git when you want `--init-git` to work

1) Preview what will happen (safe — no files or packages changed):

PowerShell / CMD (Windows)

```powershell
python .\cli.py --dry-run
```

macOS / Linux

```bash
python3 ./cli.py --dry-run
```

2) Create a real project (this will create `.venv` and install Django by default):

PowerShell

```powershell
python .\cli.py C:\path\to\outdir mysite --apps users accounts
```

Or on macOS / Linux:

```bash
python3 ./cli.py ./outdir mysite --apps users accounts
```

3) Open the GUI

```powershell
python .\cli.py --gui
```

Useful CLI flags

- `--no-venv` — skip `.venv` creation
- `--init-git` — run `git init` in the generated project
- `--dry-run` — show planned actions without making changes
- `--django-version 4.2.6` — pin an exact Django version to install
- `--python-exec /path/to/python` — use a specific Python executable

---

## Project layout

- `cli.py` — simple CLI entrypoint
- `django_generator/` — the package (modular implementation)
  - `core.py` — main orchestration / `create_project`
  - `venv_ops.py` — virtualenv and Django install helpers
  - `fs_ops.py` — filesystem operations, templates, settings/urls patching, sanitizer
  - `templates.py` — HTML/CSS templates used when generator-provided assets are missing
  - `helpers.py` — logging and subprocess helpers
  - `gui_app.py` — Tkinter GUI class
- `django_generator.py` — compatibility shim (keeps older usage working)

## Troubleshooting

- TemplateSyntaxError on `{% static %}`: run the sanitizer to inject `{% load static %}` into `templates/base.html`:

PowerShell

```powershell
python - <<'PY'
from pathlib import Path
from django_generator.fs_ops import sanitize_templates
sanitize_templates(Path(r'C:\path\to\generated_project'), cb=print)
PY
```

- Virtualenv or pip errors: try `--no-venv` and provide `--python-exec` pointing to a Python that already has Django installed