import os
import sys
import subprocess
import threading
from pathlib import Path
import textwrap
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .core import create_project
from .helpers import log, LOG_FILE

__version__ = "1.0.0"


class DjangoGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Django Project Generator v{__version__}")
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

        self.gitignore_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Add .gitignore file", variable=self.gitignore_var).grid(row=13, column=0, columnspan=2, sticky="w")

        ttk.Button(left, text="Create Project", command=self._on_create).grid(row=14, column=0, columnspan=2, sticky="we", pady=(12, 0))
        ttk.Button(left, text="Open Log File", command=self._open_log).grid(row=15, column=0, columnspan=2, sticky="we", pady=(6, 0))
        ttk.Button(left, text="Need Help?", command=self._show_help).grid(row=16, column=0, columnspan=2, sticky="we", pady=(6, 0))

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
        self.after(0, _safe)

    def _on_create(self):
        dest = self.path_var.get().strip()
        name = self.project_var.get().strip()
        python_exec = self.python_var.get().strip() or ""
        apps = [a.strip() for a in self.apps_var.get().split(",") if a.strip()]

        if not name:
            messagebox.showerror("Error", "Project name required.")
            return

        confirm = messagebox.askyesno(
            "Confirm Project Creation",
            f"Are you sure you want to create '{name}' at:\n\n{dest}?"
        )

        if not confirm:
            self.status_var.set("Cancelled.")
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
            if self.gitignore_var.get():
                from .fs_ops import create_gitignore
                create_gitignore(Path(dest), cb=self._append_log)

            self.status_var.set("Done.")

            resp = messagebox.askyesno(
                "Success 🎉",
                "✅ Django project created successfully!\n\n"
                "Do you want to open it in VSCode?"
            )
            if resp:
                self._open_vscode(dest)

            run_resp = messagebox.askyesno(
                "Launch Server?",
                "Would you like to start Django’s development server now?"
            )
            if run_resp:
                self._launch_runserver(dest, name)

        except Exception as e:
            import traceback
            self._append_log(traceback.format_exc())
            self.status_var.set("Error.")
            messagebox.showerror("Error", str(e))

    def _launch_runserver(self, dest, project_name):
        try:
            manage_py = Path(dest) / "manage.py"
            if not manage_py.exists():
                messagebox.showerror("Error", "manage.py not found. Cannot runserver.")
                return

            shell_flag = os.name == "nt"
            log(self._append_log, f"🚀 Starting Django development server for {project_name} ...")

            subprocess.Popen(
                [sys.executable, str(manage_py), "runserver"],
                cwd=str(dest),
                shell=shell_flag
            )
            messagebox.showinfo("Server Running", "Django development server started.\nCheck your terminal window.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch runserver: {e}")

    def _open_log(self):
        try:
            if not LOG_FILE.exists():
                messagebox.showinfo("Log File", "No log file found yet.")
                return
            if sys.platform.startswith("win"):
                os.startfile(LOG_FILE)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", LOG_FILE])
            else:
                subprocess.run(["xdg-open", LOG_FILE])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open log file: {e}")

    def _show_help(self):
        help_text = (
            "How to Use Django Project Generator:\n\n"
            "1. Select the folder where you want your project to be created.\n"
            "2. Enter a project name. Avoid spaces or special characters.\n"
            "3. (Optional) Enter the path to your Python executable if you don’t want to use the default one.\n"
            "4. Check 'Create virtualenv (.venv)' if you want the tool to set up a virtual environment.\n"
            "5. Specify any Django apps you want to create, separated by commas.\n"
            "6. You can also set a specific Django version, or leave it blank to install the latest.\n"
            "7. Click 'Create Project' to start the process. Progress will appear in the log window.\n\n"
            "After generation, you can open the log file for more details or troubleshooting info.\n"
            "The created project will include basic templates, static files, and app routing by default."
        )
        messagebox.showinfo("Help - Django Project Generator", help_text)

    def _open_vscode(self, folder=None):
        folder = folder or self.path_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showerror("Error", "Project folder does not exist.")
            return
        try:
            shell_flag = os.name == "nt"
            subprocess.Popen(["code", folder], shell=shell_flag)
            log(None, f"🧠 Opened project in VSCode: {folder}")
        except FileNotFoundError:
            messagebox.showerror(
                "VSCode Not Found",
                "VSCode ('code' command) not found in PATH.\n\n"
                "Make sure VSCode is installed and 'code' CLI is enabled."
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open VSCode: {e}")
