# Phase 10 reconciliation migration.
#
# The schema changes that were previously generated into this 0005 migration
# are already part of 0004_phase10_under_review_notification in the final
# Phase 10 patch. Keeping those AddField/CreateModel operations here would
# apply the same schema changes twice on SQLite.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("support_requests", "0004_phase10_under_review_notification"),
    ]

    operations = []
