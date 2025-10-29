from pathlib import Path
from typing import List, Optional, Callable
import sys

from .helpers import log
from .venv_ops import create_virtualenv, install_django
from .fs_ops import (
    create_template_structure,
    patch_settings,
    create_urls,
    write_requirements,
    init_git,
    create_gitignore,
    create_template_structure,
    create_gitignore,
)


def create_project(
    destination: str,
    project_name: str,
    python_exec: str = "",
    create_venv: bool = True,
    apps: Optional[List[str]] = None,
    django_version: str = "",
    create_templates: bool = True,
    init_git_flag: bool = False,
    cb: Optional[Callable] = None,
    dry_run: bool = False,
) -> None:
    apps = list(apps) if apps else []
    dest = Path(destination).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    log(cb, f"📁 Destination: {dest}")

    python_path = Path(python_exec) if python_exec and Path(python_exec).exists() else None

    if create_venv:
        if dry_run:
            log(cb, f"[dry-run] would create virtualenv at: {dest / '.venv'}")
            python_path = Path(python_exec) if python_exec and Path(python_exec).exists() else Path(sys.executable)
        else:
            python_in_venv = create_virtualenv(dest, cb=cb)
            python_path = python_in_venv
    if python_path is None:
        python_path = Path(sys.executable)

    if dry_run:
        # Report planned actions and avoid side effects
        log(cb, f"[dry-run] would install Django ({django_version or 'latest'}) using: {python_path} -m pip install django{('=='+django_version) if django_version else ''}")
        log(cb, f"[dry-run] would run: {python_path} -m django startproject {project_name} . (cwd={dest})")
    else:
        install_django(python_path, django_version, cb=cb)

        # create project (manage.py lives in dest)
        from .helpers import run_command
        log(cb, f"🧱 Creating Django project '{project_name}' in {dest} ...")
        run_command([str(python_path), "-m", "django", "startproject", project_name, "."], cwd=str(dest), cb=cb)

    # create apps
    if apps:
        manage_py = dest / "manage.py"
        for app in apps:
            log(cb, f"📁 Creating app '{app}' ...")
            if dry_run:
                log(cb, f"[dry-run] would run: {python_path} {manage_py} startapp {app} (cwd={dest})")
            else:
                from .helpers import run_command
                run_command([str(python_path), str(manage_py), "startapp", app], cwd=str(dest), cb=cb)

    # patch settings, templates, urls, requirements, git
    if dry_run:
        log(cb, f"[dry-run] would patch settings.py at: {dest / project_name / 'settings.py'}")
        if apps:
            log(cb, f"[dry-run] would create project-level urls and app urls for: {apps}")
        if create_templates:
            log(cb, f"[dry-run] would create templates/static at: {dest / 'templates'} and {dest / 'static'}")
        log(cb, f"[dry-run] would write requirements.txt (pip freeze) for python: {python_path}")
        if init_git_flag:
            log(cb, f"[dry-run] would initialize git in: {dest}")
    else:
        patch_settings(dest, project_name, apps, cb=cb)
        if apps:
            create_urls(dest, project_name, apps, cb=cb)
        if create_templates:
            create_template_structure(dest, apps, cb=cb)
            # sanitize generated templates to ensure {% load static %} present
            from .fs_ops import sanitize_templates
            sanitize_templates(dest, cb=cb)
        write_requirements(python_path, dest, cb=cb)
        if init_git_flag:
            init_git(dest, cb=cb)

    log(cb, "🎉 Django project created successfully!")
