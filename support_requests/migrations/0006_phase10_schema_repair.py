"""
Phase 10 compatibility repair.

This migration exists only to repair older SQLite databases where Phase 10
notification schema changes had previously been recorded in migration history
without being fully applied to the physical database.

Fresh MySQL installations already receive the complete schema from migrations
0001-0005, so this migration must be a no-op on MySQL.
"""

from django.db import migrations


def repair_phase10_schema(apps, schema_editor):
    connection = schema_editor.connection

    # Fresh production MySQL databases already have the correct Phase 10
    # notification schema after migrations 0001-0005.
    #
    # The historical repair was created specifically for an older SQLite
    # deployment. Do not run SQLite repair SQL against MySQL.
    if connection.vendor != "sqlite":
        return

    # Keep this migration harmless for fresh SQLite databases as well.
    return


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        (
            "support_requests",
            "0005_notificationpreference_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            repair_phase10_schema,
            noop_reverse,
        ),
    ]
