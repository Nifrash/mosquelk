from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

def backfill_notification_mosques(apps, schema_editor):
    """
    Safely populate the new SupportNotification.mosque FK.

    Existing Phase 6 notifications are connected to a support request.
    The support request already knows its mosque, so use that relationship
    instead of trusting any temporary/legacy value in mosque_id.
    """
    SupportNotification = apps.get_model(
        "support_requests",
        "SupportNotification",
    )
    MosqueSupportRequest = apps.get_model(
        "support_requests",
        "MosqueSupportRequest",
    )

    # Remove any invalid value that may have been created while SQLite
    # rebuilt the legacy notification table.
    SupportNotification.objects.all().update(mosque_id=None)

    for support_request_id, mosque_id in (
        MosqueSupportRequest.objects
        .exclude(mosque_id__isnull=True)
        .values_list("id", "mosque_id")
    ):
        SupportNotification.objects.filter(
            support_request_id=support_request_id,
        ).update(
            mosque_id=mosque_id,
        )


def reverse_backfill_notification_mosques(apps, schema_editor):
    SupportNotification = apps.get_model(
        "support_requests",
        "SupportNotification",
    )

    SupportNotification.objects.all().update(mosque_id=None)
class Migration(migrations.Migration):
    """
    Phase 10 compatibility migration.

    The live project already has:
        0001_initial
        0002_support_notifications
        0003_alter_supportrequesthistory_from_status_and_more

    The original Phase 10 patch incorrectly depended on a non-existent
    0003_platform_notifications migration. This migration therefore applies the
    missing Phase 9 platform-notification schema upgrade and the Phase 10
    REQUEST_UNDER_REVIEW notification type in one forward migration.
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mosques", "0002_mosqueoperationalprofile"),
        (
            "support_requests",
            "0003_alter_supportrequesthistory_from_status_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="supportnotification",
            name="support_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="support_requests.mosquesupportrequest",
            ),
        ),
        migrations.AlterField(
            model_name="supportnotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("REQUEST_SUBMITTED", "Support Request Submitted"),
                    ("REQUEST_RESUBMITTED", "Support Request Resubmitted"),
                    ("REQUEST_UNDER_REVIEW", "Support Request Under Review"),
                    (
                        "DOCUMENTS_REQUIRED",
                        "Additional Information / Documents Required",
                    ),
                    ("REQUEST_APPROVED", "Support Request Approved"),
                    ("REQUEST_REJECTED", "Support Request Rejected"),
                    ("REQUEST_IN_PROGRESS", "Support Request In Progress"),
                    ("REQUEST_COMPLETED", "Support Request Completed"),
                    ("MOSQUE_SUBMITTED", "Mosque Registration Submitted"),
                    ("MOSQUE_APPROVED", "Mosque Registration Approved"),
                    ("MOSQUE_REJECTED", "Mosque Registration Rejected"),
                    ("MOSQUE_ACCESS_ADDED", "Mosque Access Added"),
                    ("MOSQUE_ACCESS_REMOVED", "Mosque Access Removed"),
                    ("ACCOUNT_CREATED", "Account Created"),
                    ("ACCOUNT_ACTIVATED", "Account Activated"),
                    ("ACCOUNT_DEACTIVATED", "Account Deactivated"),
                    ("ACCOUNT_ROLE_CHANGED", "Account Role Changed"),
                    ("DISTRICT_ASSIGNED", "District Assigned"),
                    (
                        "DISTRICT_ASSIGNMENT_REMOVED",
                        "District Assignment Removed",
                    ),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
        migrations.AlterModelOptions(
            name="supportnotification",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "platform notification",
                "verbose_name_plural": "platform notifications",
            },
        ),
        migrations.AlterModelOptions(
            name="supportnotificationdelivery",
            options={
                "ordering": ["-attempted_at"],
                "verbose_name": "notification delivery",
                "verbose_name_plural": "notification deliveries",
            },
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="action_url",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="actor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="generated_platform_notifications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="category",
            field=models.CharField(
                choices=[
                    ("MOSQUE", "Mosque Registration"),
                    ("SUPPORT", "Support Requests"),
                    ("ACCESS", "Mosque Access"),
                    ("ACCOUNT", "Account"),
                    ("ASSIGNMENT", "Officer Assignment"),
                    ("SYSTEM", "System"),
                ],
                db_index=True,
                default="SUPPORT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="dashboard_visible",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="language_code",
            field=models.CharField(default="en", max_length=10),
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="mosque",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="platform_notifications",
                to="mosques.mosque",
            ),
        ),

        migrations.RunPython(
            backfill_notification_mosques,
            reverse_backfill_notification_mosques,
        ),

        migrations.AddField(
            model_name="supportnotification",
            name="priority",
            field=models.CharField(
                choices=[("NORMAL", "Normal"), ("HIGH", "High")],
                db_index=True,
                default="NORMAL",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="supportnotification",
            name="source_label",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="supportnotificationdelivery",
            name="retried_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="retried_notification_deliveries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="supportnotificationdelivery",
            name="retry_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="retry_attempts",
                to="support_requests.supportnotificationdelivery",
            ),
        ),
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("dashboard_enabled", models.BooleanField(default=True)),
                ("email_enabled", models.BooleanField(default=True)),
                ("sms_enabled", models.BooleanField(default=True)),
                (
                    "notify_mosque_registration",
                    models.BooleanField(default=True),
                ),
                ("notify_support_requests", models.BooleanField(default=True)),
                ("notify_mosque_access", models.BooleanField(default=True)),
                ("notify_account_changes", models.BooleanField(default=True)),
                (
                    "notify_officer_assignments",
                    models.BooleanField(default=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "notification preference",
                "verbose_name_plural": "notification preferences",
            },
        ),
        migrations.AddIndex(
            model_name="supportnotification",
            index=models.Index(
                fields=["user", "category", "created_at"],
                name="platform_notif_category_idx",
            ),
        ),
    ]
