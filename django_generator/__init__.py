"""Top-level package exports for django_generator.

Expose create_project and the GUI app for backwards compatibility.
"""
from .core import create_project
from .gui_app import DjangoGeneratorApp

__all__ = ["create_project", "DjangoGeneratorApp"]
