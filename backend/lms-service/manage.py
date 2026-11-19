#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    base_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(base_dir / "apps"))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        from django.core.management import execute_from_command_line
        # Allow runserver to start gracefully when database is offline so /api/health/ can report status
        from django.core.management.commands import runserver
        _orig_check_migrations = runserver.Command.check_migrations

        def _safe_check_migrations(self):
            try:
                _orig_check_migrations(self)
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nWarning: Database is unreachable during startup ({exc.__class__.__name__}). Starting server..."
                    )
                )

        runserver.Command.check_migrations = _safe_check_migrations
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
