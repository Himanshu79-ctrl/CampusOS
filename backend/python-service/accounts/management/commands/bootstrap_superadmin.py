"""
Management command to securely bootstrap a Super Admin user for CampusOS Auth Service.
Used for one-time initialization in production environments (e.g., Render).
"""

import os
from django.core.management.base import BaseCommand, CommandError
from accounts.models import CustomUser


class Command(BaseCommand):
    help = (
        "Securely bootstraps a one-time Super Admin account using environment variables "
        "(SUPERADMIN_USERNAME, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)."
    )

    def handle(self, *args, **options):
        username = os.environ.get("SUPERADMIN_USERNAME", "").strip()
        email = os.environ.get("SUPERADMIN_EMAIL", "").strip()
        password = os.environ.get("SUPERADMIN_PASSWORD", "")

        missing = []
        if not username:
            missing.append("SUPERADMIN_USERNAME")
        if not email:
            missing.append("SUPERADMIN_EMAIL")
        if not password:
            missing.append("SUPERADMIN_PASSWORD")

        if missing:
            raise CommandError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Ensure SUPERADMIN_USERNAME, SUPERADMIN_EMAIL, and SUPERADMIN_PASSWORD are set."
            )

        # Check if username already exists
        existing_user = CustomUser.objects.filter(username=username).first()
        if existing_user:
            if existing_user.role == "super_admin":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Super Admin '{username}' already exists. No changes made."
                    )
                )
                return
            else:
                raise CommandError(
                    f"User '{username}' already exists with role '{existing_user.role}'. "
                    "Cannot promote existing non-superadmin accounts."
                )

        # Create the new super admin account
        try:
            user = CustomUser.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role="super_admin",
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
        except Exception as exc:
            raise CommandError(f"Failed to create superadmin user: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Super Admin '{user.username}' ({user.email}) successfully created."
            )
        )
