from django.core.management.base import BaseCommand
from django.db import transaction

from locations.models import District, Province


PROVINCES = [
    ("WP", "Western Province"),
    ("CP", "Central Province"),
    ("SP", "Southern Province"),
    ("NP", "Northern Province"),
    ("EP", "Eastern Province"),
    ("NWP", "North Western Province"),
    ("NCP", "North Central Province"),
    ("UP", "Uva Province"),
    ("SGP", "Sabaragamuwa Province"),
]

DISTRICTS = [
    ("CMB", "Colombo", "WP"),
    ("GMP", "Gampaha", "WP"),
    ("KLT", "Kalutara", "WP"),
    ("KDY", "Kandy", "CP"),
    ("MTL", "Matale", "CP"),
    ("NE", "Nuwara Eliya", "CP"),
    ("GAL", "Galle", "SP"),
    ("MAT", "Matara", "SP"),
    ("HAM", "Hambantota", "SP"),
    ("JAF", "Jaffna", "NP"),
    ("KIL", "Kilinochchi", "NP"),
    ("MAN", "Mannar", "NP"),
    ("MUL", "Mullaitivu", "NP"),
    ("VAV", "Vavuniya", "NP"),
    ("TRI", "Trincomalee", "EP"),
    ("BAT", "Batticaloa", "EP"),
    ("AMP", "Ampara", "EP"),
    ("KUR", "Kurunegala", "NWP"),
    ("PUT", "Puttalam", "NWP"),
    ("ANU", "Anuradhapura", "NCP"),
    ("POL", "Polonnaruwa", "NCP"),
    ("BAD", "Badulla", "UP"),
    ("MON", "Monaragala", "UP"),
    ("RAT", "Ratnapura", "SGP"),
    ("KEG", "Kegalle", "SGP"),
]


class Command(BaseCommand):
    help = "Seed Sri Lanka's 9 provinces and 25 administrative districts."

    @transaction.atomic
    def handle(self, *args, **options):
        province_map = {}

        for code, name_en in PROVINCES:
            province, _ = Province.objects.update_or_create(
                code=code,
                defaults={
                    "name_en": name_en,
                    "is_active": True,
                },
            )
            province_map[code] = province

        for code, name_en, province_code in DISTRICTS:
            District.objects.update_or_create(
                code=code,
                defaults={
                    "name_en": name_en,
                    "province": province_map[province_code],
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Location seed complete: "
                f"{Province.objects.count()} provinces, "
                f"{District.objects.count()} districts."
            )
        )
