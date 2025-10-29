import shutil
import textwrap
import re
from pathlib import Path
from typing import List, Optional

from .helpers import log, run_command
from . import templates


def safe_create_file(path: Path, content: str, overwrite=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return
    if path.exists() and overwrite:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")


def create_template_structure(repo_root: Path, apps: List[str], cb=None):
    generator_root = Path(__file__).parent
    source_templates = generator_root / "templates"
    source_static = generator_root / "static"
    dest_templates = repo_root / "templates"
    dest_static = repo_root / "static"

    log(cb, f"📂 Copying templates and static assets from generator ...")

    if source_templates.exists() and any(source_templates.iterdir()):
        shutil.copytree(source_templates, dest_templates, dirs_exist_ok=True)
    else:
        dest_templates.mkdir(parents=True, exist_ok=True)
        safe_create_file(dest_templates / "base.html", templates.DEFAULT_BASE_HTML)
        safe_create_file(dest_templates / "home.html", templates.DEFAULT_HOME_HTML.replace("{{ project_name }}", repo_root.name))
        safe_create_file(dest_templates / "app_index.html", templates.DEFAULT_APP_INDEX_HTML)

    if source_static.exists() and any(source_static.iterdir()):
        shutil.copytree(source_static, dest_static, dirs_exist_ok=True)
    else:
        (dest_static / "css").mkdir(parents=True, exist_ok=True)
        safe_create_file(dest_static / "css" / "style.css", templates.DEFAULT_CSS)


def patch_settings(repo_root: Path, project_name: str, apps: List[str], cb=None):
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

    if re.search(r"'DIRS'\s*:\s*\[", new_text):
        new_text = re.sub(r"'DIRS'\s*:\s*\[[^\]]*\]", "'DIRS': [BASE_DIR / 'templates']", new_text)
    elif "TEMPLATES" in new_text:
        new_text = new_text.replace(
            "'APP_DIRS': True,",
            "            'DIRS': [BASE_DIR / 'templates'],\n            'APP_DIRS': True,"
        )

    if not re.search(r"STATIC_URL\s*=", new_text):
        new_text += "\nSTATIC_URL = '/static/'\n"
    new_text = re.sub(r"STATIC_URL\s*=\s*['\"].*?['\"]", "STATIC_URL = '/static/'", new_text)
    if "STATICFILES_DIRS" not in new_text:
        new_text += "\nSTATICFILES_DIRS = [BASE_DIR / 'static']\n"

    settings_path.write_text(new_text, encoding="utf-8")
    log(cb, "🧩 settings.py patched cleanly (idempotent, safe).")


def create_urls(repo_root: Path, project_name: str, apps: List[str], cb=None):
    project_urls_path = repo_root / project_name / "urls.py"
    log(cb, "🔗 Creating/patching project urls.py ...")

    base_urls = textwrap.dedent(f"""
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

    for app in apps:
        base_urls += f"    path('{app}/', include('{app}.urls'))," + "\n"
    base_urls += "]\n"

    project_urls_path.write_text(base_urls, encoding="utf-8")

    for app in apps:
        app_dir = repo_root / app
        app_urls = app_dir / "urls.py"
        app_views = app_dir / "views.py"
        app_templates = repo_root / "templates" / app
        app_templates.mkdir(parents=True, exist_ok=True)

        safe_create_file(
            app_templates / "index.html",
            textwrap.dedent(f"""
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

        safe_create_file(
            app_urls,
            textwrap.dedent(f"""
                from django.urls import path
                from . import views

                urlpatterns = [
                    path('', views.index, name='{app}_index'),
                ]
            """),
            overwrite=True,
        )

        safe_create_file(
            app_views,
            textwrap.dedent(f"""
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


def create_gitignore(dest: Path, cb=None):
    gitignore_content = textwrap.dedent("""
        # Python
        __pycache__/
        *.py[cod]
        *.pyo
        *.pyd
        .Python
        env/
        venv/
        .venv/
        build/
        develop-eggs/
        dist/
        downloads/
        eggs/
        .eggs/
        lib/
        lib64/
        parts/
        sdist/
        var/
        *.egg-info/
        .installed.cfg
        *.egg

        # Django
        *.log
        local_settings.py
        db.sqlite3
        media/

        # VSCode
        .vscode/

        # macOS / Windows
        .DS_Store
        Thumbs.db
    """)
    safe_create_file(dest / ".gitignore", gitignore_content, overwrite=False)
    log(cb, "✅ .gitignore created.")


def init_git(dest: Path, cb=None):
    try:
        create_gitignore(dest, cb=cb)
        run_command(["git", "init"], cwd=str(dest), cb=cb)
        log(cb, "✅ Git repository initialized with .gitignore.")
    except Exception as e:
        log(cb, f"⚠️ Git initialization failed: {e}")


def sanitize_templates(repo_root: Path, cb=None):
    """Ensure base.html loads the static tag and fix common whitespace issues."""
    base = repo_root / "templates" / "base.html"
    if not base.exists():
        log(cb, f"ℹ️ No base.html found at {base}, skipping sanitize.")
        return
    text = base.read_text(encoding="utf-8")
    changed = False

    # Insert {% load static %} if missing (place after doctype or at top)
    if "{% load static %}" not in text:
        # Try after doctype
        if text.lstrip().startswith("<!doctype html>"):
            text = text.replace("<!doctype html>", "<!doctype html>\n{% load static %}", 1)
        else:
            text = "{% load static %}\n" + text
        changed = True

    # Fix accidental spaces inside href attributes around {% static ... %}
    new_text = re.sub(r"href=\"\s*\{%(.*?)%\}\s*\"", lambda m: "href=\"{%" + m.group(1).strip() + "%}\"", text)
    if new_text != text:
        text = new_text
        changed = True

    if changed:
        backup = base.with_suffix(base.suffix + ".bak")
        shutil.copy2(base, backup)
        base.write_text(text, encoding="utf-8")
        log(cb, f"🔧 Sanitized templates/base.html (backup created at {backup}).")
    else:
        log(cb, "ℹ️ templates/base.html looks good; no changes made.")
