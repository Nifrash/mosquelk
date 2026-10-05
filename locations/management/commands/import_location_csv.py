import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from locations.models import District, DivisionalSecretariat, GNDivision


def as_bool(value):
    return str(value).strip().lower() not in {"0", "false", "no", "inactive"}


class Command(BaseCommand):
    help = "Import Divisional Secretariat or GN Division master data from UTF-8 CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "level",
            choices=["ds", "gn"],
            help="Import level: ds or gn",
        )
        parser.add_argument("csv_file", help="Path to the UTF-8 CSV file")

    @transaction.atomic
    def handle(self, *args, **options):
        level = options["level"]
        filename = options["csv_file"]

        try:
            handle = open(filename, "r", encoding="utf-8-sig", newline="")
        except OSError as exc:
            raise CommandError(str(exc)) from exc

        created = 0
        updated = 0

        with handle:
            reader = csv.DictReader(handle)

            if level == "ds":
                required = {"code", "name_en", "district_code"}
            else:
                required = {"code", "name_en", "ds_code"}

            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(
                    "Missing CSV columns: " + ", ".join(sorted(missing))
                )

            for row_number, row in enumerate(reader, start=2):
                code = row.get("code", "").strip()
                name_en = row.get("name_en", "").strip()

                if not code or not name_en:
                    raise CommandError(
                        f"Row {row_number}: code and name_en are required."
                    )

                defaults = {
                    "name_en": name_en,
                    "name_ta": row.get("name_ta", "").strip(),
                    "name_ar": row.get("name_ar", "").strip(),
                    "is_active": as_bool(row.get("is_active", "1")),
                }

                if level == "ds":
                    district_code = row.get("district_code", "").strip()
                    try:
                        district = District.objects.get(code=district_code)
                    except District.DoesNotExist as exc:
                        raise CommandError(
                            f"Row {row_number}: district code "
                            f"'{district_code}' does not exist."
                        ) from exc

                    defaults["district"] = district
                    _, was_created = DivisionalSecretariat.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                else:
                    ds_code = row.get("ds_code", "").strip()
                    try:
                        ds = DivisionalSecretariat.objects.get(code=ds_code)
                    except DivisionalSecretariat.DoesNotExist as exc:
                        raise CommandError(
                            f"Row {row_number}: DS code "
                            f"'{ds_code}' does not exist."
                        ) from exc

                    defaults["divisional_secretariat"] = ds
                    _, was_created = GNDivision.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete. Created: {created}; Updated: {updated}."
            )
        )
