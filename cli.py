"""Simple CLI for the django_generator package.

Usage examples:
  python cli.py ./outdir mysite --apps app1 app2 --dry-run
  python cli.py --gui
"""
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Django project generator CLI")
    parser.add_argument("destination", nargs="?", default="./my_django_project", help="Target directory")
    parser.add_argument("project_name", nargs="?", default="mysite", help="Django project name")
    parser.add_argument("--apps", nargs="*", default=[], help="App names to create")
    parser.add_argument("--no-venv", action="store_true", help="Don't create a virtualenv")
    parser.add_argument("--init-git", action="store_true", help="Run git init")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without making changes")
    parser.add_argument("--django-version", default="", help="Specific Django version (e.g. 4.2.6)")
    parser.add_argument("--python-exec", default="", help="Path to Python executable to use")
    parser.add_argument("--no-templates", dest="create_templates", action="store_false", help="Don't create templates/static")
    parser.add_argument("--gui", action="store_true", help="Open the GUI instead of running CLI")

    args = parser.parse_args()

    if args.gui:
        # Defer import of GUI to avoid tkinter load for pure CLI usage
        from django_generator.gui_app import DjangoGeneratorApp
        app = DjangoGeneratorApp()
        app.mainloop()
        return

    from django_generator import create_project

    destination = Path(args.destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    create_project(
        destination=str(destination),
        project_name=args.project_name,
        python_exec=args.python_exec,
        create_venv=not args.no_venv,
        apps=args.apps,
        django_version=args.django_version,
        create_templates=args.create_templates,
        init_git_flag=args.init_git,
        cb=print,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
