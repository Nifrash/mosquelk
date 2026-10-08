import copy

from django.db import migrations


SUPPORT_NOTIFICATION_TABLE = "support_requests_supportnotification"
SUPPORT_REQUEST_TABLE = "support_requests_mosquesupportrequest"
DELIVERY_TABLE = "support_requests_supportnotificationdelivery"
PREFERENCE_TABLE = "support_requests_notificationpreference"
USER_TABLE = "accounts_user"
MOSQUE_TABLE = "mosques_mosque"


def _table_names(connection):
    return set(connection.introspection.table_names())


def _column_map(connection, table_name):
    with connection.cursor() as cursor:
        return {
            column.name: column
            for column in connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }


def _column_names(connection, table_name):
    return set(_column_map(connection, table_name))


def _sqlite_add_column(schema_editor, table_name, column_name, definition):
    connection = schema_editor.connection

    if column_name in _column_names(connection, table_name):
        return

    qn = schema_editor.quote_name

    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER TABLE {qn(table_name)} "
            f"ADD COLUMN {qn(column_name)} {definition}"
        )


def _clean_invalid_fk(
    schema_editor,
    table_name,
    column_name,
    target_table,
    target_column="id",
):
    connection = schema_editor.connection
    tables = _table_names(connection)

    if table_name not in tables or target_table not in tables:
        return

    columns = _column_names(connection, table_name)
    target_columns = _column_names(connection, target_table)

    if column_name not in columns or target_column not in target_columns:
        return

    qn = schema_editor.quote_name

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {qn(table_name)}
               SET {qn(column_name)} = NULL
             WHERE {qn(column_name)} IS NOT NULL
               AND NOT EXISTS (
                    SELECT 1
                      FROM {qn(target_table)} AS target_table
                     WHERE target_table.{qn(target_column)}
                           = {qn(table_name)}.{qn(column_name)}
               )
            """
        )


def _sanitize_support_notification(schema_editor):
    connection = schema_editor.connection

    if SUPPORT_NOTIFICATION_TABLE not in _table_names(connection):
        return

    columns = _column_names(connection, SUPPORT_NOTIFICATION_TABLE)
    qn = schema_editor.quote_name
    table = qn(SUPPORT_NOTIFICATION_TABLE)

    _clean_invalid_fk(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "actor_id",
        USER_TABLE,
    )
    _clean_invalid_fk(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "mosque_id",
        MOSQUE_TABLE,
    )
    _clean_invalid_fk(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "user_id",
        USER_TABLE,
    )
    _clean_invalid_fk(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "support_request_id",
        SUPPORT_REQUEST_TABLE,
    )

    with connection.cursor() as cursor:
        if "action_url" in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                   SET {qn("action_url")} = ''
                 WHERE {qn("action_url")} IS NULL
                    OR {qn("action_url")} = 'action_url'
                """
            )

        if "source_label" in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                   SET {qn("source_label")} = ''
                 WHERE {qn("source_label")} IS NULL
                    OR {qn("source_label")} = 'source_label'
                """
            )

        if "language_code" in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                   SET {qn("language_code")} = 'en'
                 WHERE {qn("language_code")} IS NULL
                    OR {qn("language_code")} = ''
                    OR {qn("language_code")} = 'language_code'
                """
            )

        if "category" in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                   SET {qn("category")} = 'SUPPORT'
                 WHERE {qn("category")} IS NULL
                    OR {qn("category")} NOT IN (
                        'MOSQUE',
                        'SUPPORT',
                        'ACCESS',
                        'ACCOUNT',
                        'ASSIGNMENT',
                        'SYSTEM'
                    )
                """
            )

        if "priority" in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                   SET {qn("priority")} = 'NORMAL'
                 WHERE {qn("priority")} IS NULL
                    OR {qn("priority")} NOT IN ('NORMAL', 'HIGH')
                """
            )

        if "dashboard_visible" in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                   SET {qn("dashboard_visible")} = 1
                 WHERE {qn("dashboard_visible")} IS NULL
                    OR CAST({qn("dashboard_visible")} AS TEXT)
                       NOT IN ('0', '1')
                """
            )


def _sanitize_delivery(schema_editor):
    connection = schema_editor.connection

    if DELIVERY_TABLE not in _table_names(connection):
        return

    _clean_invalid_fk(
        schema_editor,
        DELIVERY_TABLE,
        "retried_by_id",
        USER_TABLE,
    )
    _clean_invalid_fk(
        schema_editor,
        DELIVERY_TABLE,
        "retry_of_id",
        DELIVERY_TABLE,
    )


def _backfill_mosque(schema_editor):
    connection = schema_editor.connection
    tables = _table_names(connection)

    if (
        SUPPORT_NOTIFICATION_TABLE not in tables
        or SUPPORT_REQUEST_TABLE not in tables
    ):
        return

    support_columns = _column_names(
        connection,
        SUPPORT_NOTIFICATION_TABLE,
    )
    request_columns = _column_names(
        connection,
        SUPPORT_REQUEST_TABLE,
    )

    if not {
        "mosque_id",
        "support_request_id",
    }.issubset(support_columns):
        return

    if not {"id", "mosque_id"}.issubset(request_columns):
        return

    qn = schema_editor.quote_name

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {qn(SUPPORT_NOTIFICATION_TABLE)}
               SET {qn("mosque_id")} = (
                    SELECT request_table.{qn("mosque_id")}
                      FROM {qn(SUPPORT_REQUEST_TABLE)} AS request_table
                     WHERE request_table.{qn("id")}
                           = {qn(SUPPORT_NOTIFICATION_TABLE)}.{qn("support_request_id")}
               )
             WHERE {qn("support_request_id")} IS NOT NULL
               AND EXISTS (
                    SELECT 1
                      FROM {qn(SUPPORT_REQUEST_TABLE)} AS request_table
                     WHERE request_table.{qn("id")}
                           = {qn(SUPPORT_NOTIFICATION_TABLE)}.{qn("support_request_id")}
               )
            """
        )


def _sqlite_repair_notification_columns(schema_editor):
    qn = schema_editor.quote_name

    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "action_url",
        "varchar(500) NOT NULL DEFAULT ''",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "actor_id",
        f"bigint NULL REFERENCES {qn(USER_TABLE)} ({qn('id')}) "
        "DEFERRABLE INITIALLY DEFERRED",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "category",
        "varchar(20) NOT NULL DEFAULT 'SUPPORT'",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "dashboard_visible",
        "bool NOT NULL DEFAULT 1",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "language_code",
        "varchar(10) NOT NULL DEFAULT 'en'",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "mosque_id",
        f"bigint NULL REFERENCES {qn(MOSQUE_TABLE)} ({qn('id')}) "
        "DEFERRABLE INITIALLY DEFERRED",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "priority",
        "varchar(10) NOT NULL DEFAULT 'NORMAL'",
    )
    _sqlite_add_column(
        schema_editor,
        SUPPORT_NOTIFICATION_TABLE,
        "source_label",
        "varchar(160) NOT NULL DEFAULT ''",
    )

    _sqlite_add_column(
        schema_editor,
        DELIVERY_TABLE,
        "retried_by_id",
        f"bigint NULL REFERENCES {qn(USER_TABLE)} ({qn('id')}) "
        "DEFERRABLE INITIALLY DEFERRED",
    )
    _sqlite_add_column(
        schema_editor,
        DELIVERY_TABLE,
        "retry_of_id",
        f"bigint NULL REFERENCES {qn(DELIVERY_TABLE)} ({qn('id')}) "
        "DEFERRABLE INITIALLY DEFERRED",
    )


def _ensure_sqlite_indexes(schema_editor):
    connection = schema_editor.connection
    tables = _table_names(connection)
    qn = schema_editor.quote_name

    statements = []

    if SUPPORT_NOTIFICATION_TABLE in tables:
        columns = _column_names(connection, SUPPORT_NOTIFICATION_TABLE)

        if {"user_id", "category", "created_at"}.issubset(columns):
            statements.append(
                f"""
                CREATE INDEX IF NOT EXISTS
                    {qn("platform_notif_category_idx")}
                ON {qn(SUPPORT_NOTIFICATION_TABLE)}
                    ({qn("user_id")}, {qn("category")}, {qn("created_at")})
                """
            )

        for index_name, column_name in (
            ("phase10_notif_actor_idx", "actor_id"),
            ("phase10_notif_category_idx", "category"),
            ("phase10_notif_dashboard_idx", "dashboard_visible"),
            ("phase10_notif_mosque_idx", "mosque_id"),
            ("phase10_notif_priority_idx", "priority"),
        ):
            if column_name in columns:
                statements.append(
                    f"""
                    CREATE INDEX IF NOT EXISTS {qn(index_name)}
                    ON {qn(SUPPORT_NOTIFICATION_TABLE)}
                       ({qn(column_name)})
                    """
                )

    if DELIVERY_TABLE in tables:
        columns = _column_names(connection, DELIVERY_TABLE)

        for index_name, column_name in (
            ("phase10_delivery_retried_idx", "retried_by_id"),
            ("phase10_delivery_retryof_idx", "retry_of_id"),
        ):
            if column_name in columns:
                statements.append(
                    f"""
                    CREATE INDEX IF NOT EXISTS {qn(index_name)}
                    ON {qn(DELIVERY_TABLE)}
                       ({qn(column_name)})
                    """
                )

    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def _repair_notification_preference(apps, schema_editor):
    connection = schema_editor.connection
    NotificationPreference = apps.get_model(
        "support_requests",
        "NotificationPreference",
    )

    tables = _table_names(connection)

    if PREFERENCE_TABLE not in tables:
        schema_editor.create_model(NotificationPreference)
        return

    columns = _column_names(connection, PREFERENCE_TABLE)

    if "user_id" not in columns:
        if connection.vendor == "sqlite":
            qn = schema_editor.quote_name
            _sqlite_add_column(
                schema_editor,
                PREFERENCE_TABLE,
                "user_id",
                f"bigint NULL REFERENCES {qn(USER_TABLE)} ({qn('id')}) "
                "DEFERRABLE INITIALLY DEFERRED",
            )
        else:
            field = NotificationPreference._meta.get_field("user")
            schema_editor.add_field(NotificationPreference, field)

    _clean_invalid_fk(
        schema_editor,
        PREFERENCE_TABLE,
        "user_id",
        USER_TABLE,
    )

    columns = _column_names(connection, PREFERENCE_TABLE)

    if "user_id" in columns:
        qn = schema_editor.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                DELETE FROM {qn(PREFERENCE_TABLE)}
                 WHERE {qn("user_id")} IS NULL
                """
            )

            if connection.vendor == "sqlite":
                cursor.execute(
                    f"""
                    CREATE UNIQUE INDEX IF NOT EXISTS
                        {qn("phase10_pref_user_uniq")}
                    ON {qn(PREFERENCE_TABLE)} ({qn("user_id")})
                    """
                )


def _repair_support_request_nullability(apps, schema_editor):
    connection = schema_editor.connection

    if SUPPORT_NOTIFICATION_TABLE not in _table_names(connection):
        return

    column_map = _column_map(
        connection,
        SUPPORT_NOTIFICATION_TABLE,
    )

    info = column_map.get("support_request_id")
    if info is None:
        return

    if getattr(info, "null_ok", True):
        return

    SupportNotification = apps.get_model(
        "support_requests",
        "SupportNotification",
    )

    new_field = SupportNotification._meta.get_field("support_request")
    old_field = copy.deepcopy(new_field)
    old_field.null = False
    old_field.blank = False

    schema_editor.alter_field(
        SupportNotification,
        old_field,
        new_field,
        strict=False,
    )


def _repair_non_sqlite_columns(apps, schema_editor):
    connection = schema_editor.connection

    SupportNotification = apps.get_model(
        "support_requests",
        "SupportNotification",
    )
    SupportNotificationDelivery = apps.get_model(
        "support_requests",
        "SupportNotificationDelivery",
    )

    if SUPPORT_NOTIFICATION_TABLE in _table_names(connection):
        columns = _column_names(
            connection,
            SUPPORT_NOTIFICATION_TABLE,
        )

        for field_name in (
            "action_url",
            "actor",
            "category",
            "dashboard_visible",
            "language_code",
            "mosque",
            "priority",
            "source_label",
        ):
            field = SupportNotification._meta.get_field(field_name)
            if field.column not in columns:
                schema_editor.add_field(
                    SupportNotification,
                    field,
                )
                columns = _column_names(
                    connection,
                    SUPPORT_NOTIFICATION_TABLE,
                )

    if DELIVERY_TABLE in _table_names(connection):
        columns = _column_names(connection, DELIVERY_TABLE)

        for field_name in ("retried_by", "retry_of"):
            field = SupportNotificationDelivery._meta.get_field(
                field_name
            )
            if field.column not in columns:
                schema_editor.add_field(
                    SupportNotificationDelivery,
                    field,
                )
                columns = _column_names(
                    connection,
                    DELIVERY_TABLE,
                )


def repair_phase10_schema(apps, schema_editor):
    connection = schema_editor.connection
    tables = _table_names(connection)

    if SUPPORT_NOTIFICATION_TABLE not in tables:
        raise RuntimeError(
            f"Required table {SUPPORT_NOTIFICATION_TABLE!r} does not exist."
        )

    if DELIVERY_TABLE not in tables:
        raise RuntimeError(
            f"Required table {DELIVERY_TABLE!r} does not exist."
        )

    _sanitize_support_notification(schema_editor)
    _sanitize_delivery(schema_editor)

    if connection.vendor == "sqlite":
        _sqlite_repair_notification_columns(schema_editor)
    else:
        _repair_non_sqlite_columns(apps, schema_editor)

    _sanitize_support_notification(schema_editor)
    _sanitize_delivery(schema_editor)

    _backfill_mosque(schema_editor)

    _repair_notification_preference(
        apps,
        schema_editor,
    )

    _repair_support_request_nullability(
        apps,
        schema_editor,
    )

    _sanitize_support_notification(schema_editor)
    _sanitize_delivery(schema_editor)
    _backfill_mosque(schema_editor)

    if connection.vendor == "sqlite":
        _ensure_sqlite_indexes(schema_editor)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False

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
