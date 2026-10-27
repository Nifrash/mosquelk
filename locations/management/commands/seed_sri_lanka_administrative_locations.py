from __future__ import annotations

import re
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from locations.models import District, DivisionalSecretariat, GNDivision


OFFICIAL_DCS_XLSX_URL = "https://www.statistics.gov.lk/qlink/AdminDivCodes_Excel"

# Official DCS District_Code restarts inside each Province.
# Therefore the correct DCS district identity is:
#     (Province_Code, District_Code)
# -> project District.code
DCS_TO_PROJECT_DISTRICT_CODE = {
    ("1", "1"): "CMB",
    ("1", "2"): "GMP",
    ("1", "3"): "KLT",

    ("2", "1"): "KDY",
    ("2", "2"): "MTL",
    ("2", "3"): "NE",

    ("3", "1"): "GAL",
    ("3", "2"): "MAT",
    ("3", "3"): "HAM",

    ("4", "1"): "JAF",
    ("4", "2"): "KIL",
    ("4", "3"): "MAN",
    ("4", "4"): "VAV",
    ("4", "5"): "MUL",

    ("5", "1"): "BAT",
    ("5", "2"): "AMP",
    ("5", "3"): "TRI",

    ("6", "1"): "KUR",
    ("6", "2"): "PUT",

    ("7", "1"): "ANU",
    ("7", "2"): "POL",

    ("8", "1"): "BAD",
    ("8", "2"): "MON",

    ("9", "1"): "RAT",
    ("9", "2"): "KEG",
}

# Fallback aliases only. The primary mapping above is by official DCS district code.
DISTRICT_NAME_ALIASES = {
    "colombo": "CMB",
    "gampaha": "GMP",
    "kalutara": "KLT",
    "kandy": "KDY",
    "matale": "MTL",
    "nuwara eliya": "NE",
    "galle": "GAL",
    "matara": "MAT",
    "hambantota": "HAM",
    "jaffna": "JAF",
    "kilinochchi": "KIL",
    "mannar": "MAN",
    "vavuniya": "VAV",
    "mullaitivu": "MUL",
    "mullativu": "MUL",
    "batticaloa": "BAT",
    "ampara": "AMP",
    "trincomalee": "TRI",
    "kurunegala": "KUR",
    "puttalam": "PUT",
    "anuradhapura": "ANU",
    "polonnaruwa": "POL",
    "badulla": "BAD",
    "monaragala": "MON",
    "moneragala": "MON",
    "ratnapura": "RAT",
    "rathnapura": "RAT",
    "kegalle": "KEG",
}

EXPECTED_HEADERS = {
    "GND_UID",
    "District_Code",
    "District_Name",
    "DSD_Code",
    "DSD_Name",
    "GND_Name",
}

XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def clean_text(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.endswith(".0") and value[:-2].isdigit():
        return value[:-2]
    return value


def digits_only(value):
    return "".join(ch for ch in clean_text(value) if ch.isdigit())


def normalize_header(value):
    return re.sub(r"[^a-z0-9]+", "_", clean_text(value).lower()).strip("_")


def normalize_numeric_code(value):
    digits = digits_only(value)
    if not digits:
        return ""
    return str(int(digits))


def excel_column_index(cell_reference):
    letters = "".join(ch for ch in cell_reference if ch.isalpha())
    result = 0
    for char in letters.upper():
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result - 1


def load_shared_strings(archive):
    filename = "xl/sharedStrings.xml"
    if filename not in archive.namelist():
        return []

    root = ET.fromstring(archive.read(filename))
    strings = []

    for item in root.findall(f"{{{XML_NS}}}si"):
        parts = []
        for text_node in item.iter(f"{{{XML_NS}}}t"):
            parts.append(text_node.text or "")
        strings.append("".join(parts))

    return strings


def get_sheet_path(archive, preferred_name="GNDList"):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

    rel_targets = {}
    for rel in rels.findall(f"{{{REL_NS}}}Relationship"):
        rel_targets[rel.attrib["Id"]] = rel.attrib["Target"]

    sheets = workbook.find(f"{{{XML_NS}}}sheets")
    if sheets is None:
        raise CommandError("The DCS workbook does not contain any worksheet.")

    selected = None
    first = None

    for sheet in sheets.findall(f"{{{XML_NS}}}sheet"):
        relation_id = sheet.attrib.get(f"{{{DOC_REL_NS}}}id")
        target = rel_targets.get(relation_id)

        if not target:
            continue

        if first is None:
            first = target

        if clean_text(sheet.attrib.get("name")).lower() == preferred_name.lower():
            selected = target
            break

    target = selected or first
    if not target:
        raise CommandError("Could not locate the worksheet inside the DCS workbook.")

    target = target.replace("\\", "/").lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target

    return target


def iter_xlsx_rows(filename):
    """
    Read the DCS XLSX using only Python's standard library.

    This avoids adding openpyxl/pandas as a production dependency.
    """
    with zipfile.ZipFile(filename, "r") as archive:
        shared_strings = load_shared_strings(archive)
        sheet_path = get_sheet_path(archive)

        if sheet_path not in archive.namelist():
            raise CommandError(
                f"Could not find worksheet file '{sheet_path}' in the DCS workbook."
            )

        sheet_root = ET.fromstring(archive.read(sheet_path))
        sheet_data = sheet_root.find(f"{{{XML_NS}}}sheetData")

        if sheet_data is None:
            raise CommandError("The DCS worksheet does not contain sheet data.")

        for row in sheet_data.findall(f"{{{XML_NS}}}row"):
            values = {}

            for cell in row.findall(f"{{{XML_NS}}}c"):
                reference = cell.attrib.get("r", "")
                column_index = excel_column_index(reference)
                cell_type = cell.attrib.get("t", "")

                value = ""

                if cell_type == "inlineStr":
                    inline = cell.find(f"{{{XML_NS}}}is")
                    if inline is not None:
                        value = "".join(
                            node.text or ""
                            for node in inline.iter(f"{{{XML_NS}}}t")
                        )
                else:
                    value_node = cell.find(f"{{{XML_NS}}}v")
                    raw = value_node.text if value_node is not None else ""

                    if cell_type == "s" and raw != "":
                        try:
                            value = shared_strings[int(raw)]
                        except (ValueError, IndexError):
                            value = raw
                    else:
                        value = raw or ""

                values[column_index] = clean_text(value)

            if not values:
                continue

            max_index = max(values)
            yield [values.get(index, "") for index in range(max_index + 1)]


def read_dcs_records(filename):
    rows = iter_xlsx_rows(filename)

    try:
        headers = next(rows)
    except StopIteration as exc:
        raise CommandError("The DCS workbook is empty.") from exc

    normalized = [normalize_header(item) for item in headers]
    header_map = {name: index for index, name in enumerate(normalized)}

    required = {
        "gnd_uid",
        "province_code",
        "province_name",
        "district_code",
        "district_name",
        "dsd_code",
        "dsd_name",
        "gnd_name",
    }

    missing = required - set(header_map)
    if missing:
        raise CommandError(
            "DCS workbook format has changed. Missing columns: "
            + ", ".join(sorted(missing))
        )

    def get(row, field):
        index = header_map[field]
        if index >= len(row):
            return ""
        return clean_text(row[index])

    for row_number, row in enumerate(rows, start=2):
        gnd_uid = digits_only(get(row, "gnd_uid"))
        province_code = normalize_numeric_code(get(row, "province_code"))
        province_name = get(row, "province_name")
        district_code = normalize_numeric_code(get(row, "district_code"))
        district_name = get(row, "district_name")
        dsd_code = normalize_numeric_code(get(row, "dsd_code"))
        dsd_name = get(row, "dsd_name")
        gnd_name = get(row, "gnd_name")

        if not all(
            [
                gnd_uid,
                province_code,
                province_name,
                district_code,
                district_name,
                dsd_code,
                dsd_name,
                gnd_name,
            ]
        ):
            # Ignore trailing notes/blank rows but fail on a partially populated data row.
            meaningful = any(clean_text(value) for value in row)
            if meaningful:
                raise CommandError(
                    f"Row {row_number}: required administrative fields are missing."
                )
            continue

        yield {
            "row_number": row_number,
            "gnd_uid": gnd_uid,
            "province_code": province_code,
            "province_name": province_name,
            "district_code": district_code,
            "district_name": district_name,
            "dsd_code": dsd_code,
            "dsd_name": dsd_name,
            "gnd_name": gnd_name,
        }


def download_official_workbook(target):
    target.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        OFFICIAL_DCS_XLSX_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 MosqueSriLankaLocationImporter/1.0 "
                "(Django management command)"
            )
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except Exception as exc:
        raise CommandError(
            "Could not download the official DCS Administrative Division Codes "
            f"workbook from {OFFICIAL_DCS_XLSX_URL}. "
            "Download the Excel file manually from the DCS website and run this "
            "command again with --file PATH_TO_XLSX. "
            f"Original error: {exc}"
        ) from exc

    if not content.startswith(b"PK"):
        raise CommandError(
            "The downloaded DCS file is not a valid XLSX file. "
            "Please download it manually and use --file."
        )

    target.write_bytes(content)
    return target


class Command(BaseCommand):
    help = (
        "Seed Sri Lanka Divisional Secretariats and GN Divisions from the "
        "official Department of Census and Statistics Administrative Division "
        "Codes workbook."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="source_file",
            default="",
            help=(
                "Use an already-downloaded DCS XLSX file instead of downloading "
                "the official workbook."
            ),
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Re-download the official workbook even if a cached copy exists.",
        )

    def _find_project_district(
        self,
        province_code,
        district_code,
        official_name,
    ):
        project_code = DCS_TO_PROJECT_DISTRICT_CODE.get(
            (province_code, district_code)
        )

        if project_code:
            district = District.objects.filter(code=project_code).first()
            if district:
                return district

        alias_code = DISTRICT_NAME_ALIASES.get(
            official_name.strip().lower()
        )
        if alias_code:
            district = District.objects.filter(code=alias_code).first()
            if district:
                return district

        return District.objects.filter(
            name_en__iexact=official_name.strip()
        ).first()

    @transaction.atomic
    def handle(self, *args, **options):
        source_file = options["source_file"].strip()

        if source_file:
            workbook = Path(source_file).expanduser().resolve()
            if not workbook.exists():
                raise CommandError(f"File does not exist: {workbook}")
        else:
            cache_dir = Path(__file__).resolve().parents[2] / "data" / "cache"
            workbook = cache_dir / "GNDList_Final.xlsx"

            if options["refresh"] or not workbook.exists():
                self.stdout.write(
                    "Downloading official DCS Administrative Division Codes..."
                )
                download_official_workbook(workbook)
            else:
                self.stdout.write(f"Using cached workbook: {workbook}")

        records = list(read_dcs_records(workbook))

        if not records:
            raise CommandError("No GN Division records were found in the workbook.")

        # The official register can legitimately contain the same English GN
        # name more than once under one Divisional Secretariat. GNDivision.code
        # (official GND_UID) is therefore the identity used by this importer.
        seen_gn_names = set()
        duplicate_gn_names = set()

        for record in records:
            name_key = (
                record["province_code"],
                record["district_code"],
                record["dsd_code"],
                record["gnd_name"].strip().casefold(),
            )
            if name_key in seen_gn_names:
                duplicate_gn_names.add(name_key)
            else:
                seen_gn_names.add(name_key)

        missing_districts = {}
        ds_created = 0
        ds_updated = 0
        gn_created = 0
        gn_updated = 0
        ds_cache = {}

        for record in records:
            district = self._find_project_district(
                record["province_code"],
                record["district_code"],
                record["district_name"],
            )

            if district is None:
                missing_districts[
                    (
                        record["province_code"],
                        record["district_code"],
                        record["district_name"],
                    )
                ] = True
                continue

            # DSD_Code is not globally unique by itself, and District_Code
            # also restarts inside each Province. The stable DS identity is
            # Province_Code + District_Code + DSD_Code.
            ds_key = (
                record["province_code"],
                record["district_code"],
                record["dsd_code"],
            )

            ds = ds_cache.get(ds_key)

            if ds is None:
                ds_code = (
                    "DCS-DS-"
                    f"{record['province_code']}-"
                    f"{record['district_code']}-"
                    f"{record['dsd_code']}"
                )

                # First prefer the corrected official code.
                ds = DivisionalSecretariat.objects.filter(
                    code=ds_code
                ).first()

                was_created = False

                if ds is None:
                    # Repair support for the first importer version:
                    # reuse the matching collapsed DS row where possible
                    # rather than creating a duplicate name in the district.
                    ds = DivisionalSecretariat.objects.filter(
                        district=district,
                        name_en__iexact=record["dsd_name"],
                    ).first()

                    if ds is None:
                        ds = DivisionalSecretariat.objects.create(
                            code=ds_code,
                            district=district,
                            name_en=record["dsd_name"],
                            is_active=True,
                        )
                        was_created = True
                    else:
                        changed = False

                        if ds.code != ds_code:
                            ds.code = ds_code
                            changed = True

                        if ds.district_id != district.pk:
                            ds.district = district
                            changed = True

                        if ds.name_en != record["dsd_name"]:
                            ds.name_en = record["dsd_name"]
                            changed = True

                        if not ds.is_active:
                            ds.is_active = True
                            changed = True

                        if changed:
                            ds.save(
                                update_fields=[
                                    "code",
                                    "district",
                                    "name_en",
                                    "is_active",
                                ]
                            )
                else:
                    changed = False

                    if ds.district_id != district.pk:
                        ds.district = district
                        changed = True

                    if ds.name_en != record["dsd_name"]:
                        ds.name_en = record["dsd_name"]
                        changed = True

                    if not ds.is_active:
                        ds.is_active = True
                        changed = True

                    if changed:
                        ds.save(
                            update_fields=[
                                "district",
                                "name_en",
                                "is_active",
                            ]
                        )

                ds_cache[ds_key] = ds

                if was_created:
                    ds_created += 1
                else:
                    ds_updated += 1

            gn_code = record["gnd_uid"]

            _, was_created = GNDivision.objects.update_or_create(
                code=gn_code,
                defaults={
                    "divisional_secretariat": ds,
                    "name_en": record["gnd_name"],
                    "is_active": True,
                },
            )

            if was_created:
                gn_created += 1
            else:
                gn_updated += 1

        # Any DS rows left behind by the first broken importer use the old
        # two-part DCS-DS-<district>-<dsd> code. They should not appear in
        # dropdowns after the hierarchy has been repaired.
        repaired_ds_ids = {
            ds.pk for ds in ds_cache.values()
        }

        stale_legacy_count = 0

        legacy_candidates = DivisionalSecretariat.objects.filter(
            code__startswith="DCS-DS-",
            is_active=True,
        ).exclude(pk__in=repaired_ds_ids)

        for legacy_ds in legacy_candidates:
            suffix = legacy_ds.code.removeprefix("DCS-DS-")
            if len(suffix.split("-")) == 2:
                legacy_ds.is_active = False
                legacy_ds.save(update_fields=["is_active"])
                stale_legacy_count += 1

        if missing_districts:
            details = ", ".join(
                f"P{province_code}/D{district_code} {name}"
                for province_code, district_code, name
                in sorted(missing_districts)
            )
            raise CommandError(
                "The project is missing district master records required by the "
                "DCS data: "
                + details
                + ". Run 'python manage.py seed_sri_lanka_locations' first."
            )

        ds_total = DivisionalSecretariat.objects.filter(is_active=True).count()
        gn_total = GNDivision.objects.filter(is_active=True).count()

        self.stdout.write(
            self.style.SUCCESS(
                "Sri Lanka administrative location import completed successfully."
            )
        )
        self.stdout.write(
            f"Source workbook: {workbook}"
        )
        self.stdout.write(
            f"Divisional Secretariats - Created: {ds_created}; "
            f"Updated: {ds_updated}; Active total: {ds_total}"
        )
        self.stdout.write(
            f"GN Divisions - Created: {gn_created}; "
            f"Updated: {gn_updated}; Active total: {gn_total}"
        )
        self.stdout.write(
            f"Legacy collapsed DS rows deactivated: {stale_legacy_count}"
        )

        if duplicate_gn_names:
            self.stdout.write(
                self.style.WARNING(
                    "Official source contains "
                    f"{len(duplicate_gn_names)} repeated GN name(s) within the "
                    "same DS. They were preserved as separate official records "
                    "using their unique GND_UID codes."
                )
            )

        if not (330 <= ds_total <= 350):
            self.stdout.write(
                self.style.WARNING(
                    "DS total is outside the expected national range. "
                    "Please review the DCS workbook/version."
                )
            )

        if not (13500 <= gn_total <= 14500):
            self.stdout.write(
                self.style.WARNING(
                    "GN total is outside the expected national range. "
                    "Please review the DCS workbook/version."
                )
            )
