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

# -------------------------
# Helpers
# -------------------------
def run_command(cmd: List[str], cwd: Optional[str] = None, cb: Optional[Callable] = None) -> str:
    """Run a subprocess command safely (cross-platform), logging output incrementally."""
    try:
        # Ensure all args are strings (handles Path objects)
        cmd = [str(c) for c in cmd]
        log(cb, f"→ {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=False)
        if proc.stdout:
            for line in proc.stdout.strip().splitlines():
                log(cb, f"   {line}")
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            raise RuntimeError(err or f"Command {cmd[0]} failed with code {proc.returncode}")
        return proc.stdout.strip()
    except Exception as e:
        log(cb, f"❌ Error running {' '.join(cmd)}: {e}")
        raise

def log(cb: Optional[Callable], msg: str):
    if cb:
        cb(msg)
    else:
        print(msg)

# -------------------------
# Template defaults (used when generator/templates missing)
# -------------------------
DEFAULT_BASE_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{{ project_name|default:"My Django Project" }}</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
    <style>
      /* Minimal sensible defaults so generated projects look presentable */
      body{font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;padding:0;background:#f8f9fb;color:#222}
      header{background:#222;color:#fff;padding:12px 18px}
      main{padding:18px}
      footer{padding:12px 18px;font-size:0.9rem;color:#666}
      .container{max-width:1100px;margin:0 auto}
      h1,h2{margin:0 0 8px 0}
      .card{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(16,24,40,0.06)}
    </style>
  </head>
  <body>
    <header>
      <div class="container"><h1>{{ title|default:"My Django Project" }}</h1></div>
    </header>
    <main>
      <div class="container">
        {% block content %}{% endblock %}
      </div>
    </main>
    <footer>
      <div class="container">
        © {{ now|date:"Y" }} My Django Project — Generated automatically
      </div>
    </footer>
  </body>
</html>
"""

DEFAULT_HOME_HTML = """\
{% extends 'base.html' %}
{% load static %}
{% block content %}
  <div class="card" style="text-align:center; padding:2rem;">
    <h2>Welcome to {{ project_name|title }}</h2>
    <p>Your Django project has been generated successfully.</p>
    <p>Use the navigation bar above to open any app.</p>
  </div>
{% endblock %}
"""


DEFAULT_APP_INDEX_HTML = """\
{% extends 'base.html' %}
{% block content %}
  <div class="card">
    <h2>{{ app_title }}</h2>
    <p>This page was generated for this app module.</p>
    <p>You can edit <code>templates/app_index.html</code> to customize all new app pages.</p>
  </div>
{% endblock %}
"""

DEFAULT_CSS = """\
/* minimal style.css generated for convenience */
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
h1, h2 { color: #111; }
a { color: #0366d6; text-decoration: none; }
.container { max-width: 1100px; margin: 0 auto; padding: 12px; }
"""

# -------------------------
# Core operations
# -------------------------
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

def create_django_project(dest: Path, project_name: str, python_exe: Path, cb=None):
    log(cb, f"🧱 Creating Django project '{project_name}' in {dest} ...")
    run_command([str(python_exe), "-m", "django", "startproject", project_name, str(dest)], cb=cb)
    log(cb, "✅ Project created.")

def create_apps(dest: Path, apps: List[str], python_exe: Path, cb=None):
    if not apps:
        return
    manage_py = dest / "manage.py"
    for app in apps:
        log(cb, f"📁 Creating app '{app}' ...")
        run_command([str(python_exe), str(manage_py), "startapp", app], cwd=str(dest), cb=cb)

def safe_create_file(path: Path, content: str, overwrite=False):
    """Safely write file, avoiding accidental data loss."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        # Don’t overwrite — only create if missing
        return
    if path.exists() and overwrite:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")


def create_template_structure(repo_root: Path, apps: List[str], cb=None):
    """
    Create templates/static structure next to manage.py (repo_root).
    Uses the generator's own 'templates' and 'static' folders if available.
    """
    generator_root = Path(__file__).parent
    source_templates = generator_root / "templates"
    source_static = generator_root / "static"
    dest_templates = repo_root / "templates"
    dest_static = repo_root / "static"

    log(cb, f"📂 Copying templates and static assets from generator ...")

    # ✅ Always prefer local folders (use defaults only if missing)
    if source_templates.exists() and any(source_templates.iterdir()):
        shutil.copytree(source_templates, dest_templates, dirs_exist_ok=True)
    else:
        dest_templates.mkdir(parents=True, exist_ok=True)
        safe_create_file(dest_templates / "base.html", DEFAULT_BASE_HTML)
        safe_create_file(dest_templates / "home.html", DEFAULT_HOME_HTML.replace("{{ project_name }}", repo_root.name))
        safe_create_file(dest_templates / "app_index.html", DEFAULT_APP_INDEX_HTML)

    if source_static.exists() and any(source_static.iterdir()):
        shutil.copytree(source_static, dest_static, dirs_exist_ok=True)
    else:
        (dest_static / "css").mkdir(parents=True, exist_ok=True)
        safe_create_file(dest_static / "css" / "style.css", DEFAULT_CSS)


def patch_settings(repo_root: Path, project_name: str, apps: List[str], cb=None):
    """
    Safely patch settings.py:
    - Adds apps to INSTALLED_APPS only once.
    - Ensures template/static dirs configured properly.
    - Fully idempotent.
    """
    settings_path = repo_root / project_name / "settings.py"
    if not settings_path.exists():
        log(cb, f"⚠️ settings.py not found at {settings_path}, skipping patch.")
        return

    text = settings_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines = []
    in_apps = False

    for line in lines:
        stripped = line.strip()
        # Detect INSTALLED_APPS block
        if stripped.startswith("INSTALLED_APPS"):
            in_apps = True
            new_lines.append(line)
            continue
        if in_apps:
            if stripped.startswith("]"):
                for app in apps:
                    if f"'{app}'" not in text and f'"{app}"' not in text:
                        new_lines.append(f"    '{app}',")
                in_apps = False
        new_lines.append(line)

    new_text = "\n".join(new_lines)

    # --- Ensure TEMPLATES 'DIRS' ---
    import re
    if re.search(r"'DIRS'\s*:\s*\[", new_text):
        new_text = re.sub(r"'DIRS'\s*:\s*\[[^\]]*\]", "'DIRS': [BASE_DIR / 'templates']", new_text)
    elif "TEMPLATES" in new_text:
        new_text = new_text.replace(
            "'APP_DIRS': True,",
            "            'DIRS': [BASE_DIR / 'templates'],\n            'APP_DIRS': True,"
        )

    # --- Ensure STATIC_URL & STATICFILES_DIRS ---
    if not re.search(r"STATIC_URL\s*=", new_text):
        new_text += "\nSTATIC_URL = '/static/'\n"
    new_text = re.sub(r"STATIC_URL\s*=\s*['\"].*?['\"]", "STATIC_URL = '/static/'", new_text)
    if "STATICFILES_DIRS" not in new_text:
        new_text += "\nSTATICFILES_DIRS = [BASE_DIR / 'static']\n"

    settings_path.write_text(new_text, encoding="utf-8")
    log(cb, "🧩 settings.py patched cleanly (idempotent, safe).")


def create_urls(repo_root: Path, project_name: str, apps: List[str], cb=None):
    """
    Create project-level urls.py with:
      - home route → templates/home.html (lists all apps as buttons)
      - admin route
      - auto includes for each app (/appname/)
    Each app gets its own urls.py and views.py rendering templates/<app>/index.html.
    """
    project_urls_path = repo_root / project_name / "urls.py"
    log(cb, "🔗 Creating/patching project urls.py ...")

    # ✅ Base project urls.py — now passes app list to the template
    base_urls = textwrap.dedent(f"""\
        from django.contrib import admin
        from django.urls import path, include
        from django.shortcuts import render

        def home(request):
            apps = {apps!r}
            return render(request, 'home.html', {{
                'project_name': '{project_name}',
                'apps': apps,
            }})

        urlpatterns = [
            path('', home, name='home'),
            path('admin/', admin.site.urls),
    """)

    # ✅ Add includes for each app
    for app in apps:
        base_urls += f"    path('{app}/', include('{app}.urls')),\n"
    base_urls += "]\n"

    # Write project-level urls.py
    project_urls_path.write_text(base_urls, encoding="utf-8")

    # ✅ Create each app’s urls.py, views.py, and index.html
    for app in apps:
        app_dir = repo_root / app
        app_urls = app_dir / "urls.py"
        app_views = app_dir / "views.py"
        app_templates = repo_root / "templates" / app
        app_templates.mkdir(parents=True, exist_ok=True)

        # index.html for each app
        safe_create_file(
            app_templates / "index.html",
            textwrap.dedent(f"""\
                {{% extends 'base.html' %}}
                {{% block content %}}
                  <div class="card">
                    <h2>{app.title()} App</h2>
                    <p>This is the <strong>{app}</strong> app’s default page.</p>
                    <p>Edit <code>templates/{app}/index.html</code> to customize.</p>
                  </div>
                {{% endblock %}}
            """),
            overwrite=False,
        )

        # urls.py for each app
        safe_create_file(
            app_urls,
            textwrap.dedent(f"""\
                from django.urls import path
                from . import views

                urlpatterns = [
                    path('', views.index, name='{app}_index'),
                ]
            """),
            overwrite=True,
        )

        # views.py for each app
        safe_create_file(
            app_views,
            textwrap.dedent(f"""\
                from django.shortcuts import render

                def index(request):
                    apps = {apps!r}
                    return render(request, '{app}/index.html', {{
                        'app_title': '{app.title()}',
                        'apps': apps,
                        'project_name': '{project_name}',
                    }})
            """),
            overwrite=True,
        )



    log(cb, "✅ URLs and app views created (home + app routes).")

def write_requirements(python_exe: Path, dest: Path, cb=None):
    log(cb, "📝 Writing requirements.txt ...")
    try:
        out = run_command([str(python_exe), "-m", "pip", "freeze"], cb=cb)
        (dest / "requirements.txt").write_text(out, encoding="utf-8")
    except Exception as e:
        log(cb, f"⚠️ Could not write requirements.txt: {e}")

def init_git(dest: Path, cb=None):
    try:
        run_command(["git", "init"], cwd=str(dest), cb=cb)
        log(cb, "✅ Git repository initialized.")
    except Exception as e:
        log(cb, f"⚠️ Git init failed: {e}")

# -------------------------
# High-level create_project
# -------------------------
def create_project(
    destination: str,
    project_name: str,
    python_exec: str,
    create_venv: bool,
    apps: List[str],
    django_version: str,
    create_templates: bool,
    init_git_flag: bool,
    cb: Optional[Callable] = None
):
    dest = Path(destination).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    log(cb, f"📁 Destination: {dest}")

    python_path = Path(python_exec) if python_exec and Path(python_exec).exists() else None

    # create or reuse venv
    if create_venv:
        python_in_venv = create_virtualenv(dest, cb=cb)
        python_path = python_in_venv
    if python_path is None:
        python_path = Path(sys.executable)

    install_django(python_path, django_version, cb=cb)
    create_django_project(dest, project_name, python_path, cb=cb)
    create_apps(dest, apps, python_path, cb=cb)

    # patch settings: repo root is dest (where manage.py lives)
    patch_settings(dest, project_name, apps, cb=cb)

    # templates/static placed at repo root (next to manage.py)
    if apps:
        create_urls(dest, project_name, apps, cb=cb)

    if create_templates:
        create_template_structure(dest, apps, cb=cb)

    write_requirements(python_path, dest, cb=cb)

    if init_git_flag:
        init_git(dest, cb=cb)

    log(cb, "🎉 Django project created successfully!")

# -------------------------
# Simple GUI (kept from original)
# -------------------------
class DjangoGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Django Project Generator")
        self.geometry("1000x540")
        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        left = ttk.Frame(frm)
        left.grid(row=0, column=0, sticky="nswe", padx=(0, 12))
        right = ttk.Frame(frm)
        right.grid(row=0, column=1, sticky="nswe")

        ttk.Label(left, text="Project folder:").grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar(value=str(Path.cwd()))
        ttk.Entry(left, textvariable=self.path_var, width=40).grid(row=1, column=0, sticky="we")
        ttk.Button(left, text="Browse", command=self._browse).grid(row=1, column=1)

        ttk.Label(left, text="Project name:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.project_var = tk.StringVar(value="myproject")
        ttk.Entry(left, textvariable=self.project_var).grid(row=3, column=0, columnspan=2, sticky="we")

        ttk.Label(left, text="Python executable (optional path):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.python_var = tk.StringVar(value="")
        ttk.Entry(left, textvariable=self.python_var).grid(row=5, column=0, columnspan=2, sticky="we")

        self.venv_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Create virtualenv (.venv)", variable=self.venv_var).grid(row=6, column=0, columnspan=2, sticky="w")

        ttk.Label(left, text="Django version (optional):").grid(row=7, column=0, sticky="w", pady=(8, 0))
        self.dj_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.dj_var).grid(row=8, column=0, columnspan=2, sticky="we")

        ttk.Label(left, text="Apps (comma separated):").grid(row=9, column=0, sticky="w", pady=(8, 0))
        self.apps_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.apps_var).grid(row=10, column=0, columnspan=2, sticky="we")

        self.templates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Create templates/static folders", variable=self.templates_var).grid(row=11, column=0, columnspan=2, sticky="w")

        self.git_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Initialize git repository", variable=self.git_var).grid(row=12, column=0, columnspan=2, sticky="w")

        ttk.Button(left, text="Create Project", command=self._on_create).grid(row=13, column=0, columnspan=2, sticky="we", pady=(12, 0))

        ttk.Label(right, text="Progress log:").pack(anchor="w")
        self.log = tk.Text(right, height=25, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(6, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            self.path_var.set(folder)

    def _append_log(self, msg):
        def _safe():
            self.log.configure(state="normal")
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.after(0, _safe)  # ✅ Schedule on main thread


    def _on_create(self):
        dest = self.path_var.get()
        name = self.project_var.get().strip()
        python_exec = self.python_var.get().strip() or ""
        apps = [a.strip() for a in self.apps_var.get().split(",") if a.strip()]
        if not name:
            messagebox.showerror("Error", "Project name required.")
            return

        self.status_var.set("Running...")
        threading.Thread(
            target=self._create_thread,
            args=(dest, name, python_exec, apps),
            daemon=True,
        ).start()

    def _create_thread(self, dest, name, python_exec, apps):
        try:
            create_project(
                destination=dest,
                project_name=name,
                python_exec=python_exec,
                create_venv=self.venv_var.get(),
                apps=apps,
                django_version=self.dj_var.get(),
                create_templates=self.templates_var.get(),
                init_git_flag=self.git_var.get(),
                cb=self._append_log
            )
            self.status_var.set("Done.")
            messagebox.showinfo("Success", "✅ Django project created successfully!")
        except Exception as e:
            import traceback
            self._append_log(traceback.format_exc())
            self.status_var.set("Error.")
            messagebox.showerror("Error", str(e))

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    app = DjangoGeneratorApp()
    app.mainloop()