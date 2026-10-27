SRI LANKA ADMINISTRATIVE MASTER DATA SOURCE
===========================================

Primary source:
Department of Census and Statistics (DCS), Sri Lanka
Administrative Division Codes

Landing page:
https://www.statistics.gov.lk/qlink/AdminDivCode

Excel endpoint used by the management command:
https://www.statistics.gov.lk/qlink/AdminDivCodes_Excel

The official workbook contains the administrative hierarchy needed by this
project, including district, Divisional Secretariat Division and Grama
Niladhari Division identifiers/names.

This project importer stores:
- Divisional Secretariat name in name_en
- GN Division name in name_en
- Official GND_UID as GNDivision.code
- A stable DCS-derived DS code such as DCS-DS-52-03

Tamil and Arabic names are left blank because the official workbook used by
this importer provides the English administrative names used for matching.
They can be enriched separately without changing the hierarchy.

The downloaded workbook is cached locally under:
locations/data/cache/GNDList_Final.xlsx

The cache folder/file does not need to be committed to Git.
