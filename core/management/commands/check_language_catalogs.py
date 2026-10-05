from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Check that Tamil and Arabic compiled Django catalogs exist."

    def handle(self, *args, **options):
        missing = []
        for language in ("ta", "ar"):
            base = Path(settings.BASE_DIR) / "locale" / language / "LC_MESSAGES"
            for filename in ("django.po", "django.mo"):
                path = base / filename
                if not path.exists() or path.stat().st_size == 0:
                    missing.append(str(path))

        if missing:
            raise CommandError("Missing language catalog files: " + ", ".join(missing))

        self.stdout.write(self.style.SUCCESS("Tamil and Arabic language catalogs are present and compiled."))
