from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("support_requests", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mosquesupportrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("SUBMITTED", "Submitted"),
                    ("UNDER_REVIEW", "Under Review"),
                    ("DOCUMENTS_REQUIRED", "Additional Information / Documents Required"),
                    ("APPROVED", "Approved"),
                    ("IN_PROGRESS", "In Progress"),
                    ("COMPLETED", "Completed"),
                    ("REJECTED", "Rejected"),
                    ("CANCELLED", "Cancelled"),
                ],
                db_index=True,
                default="DRAFT",
                max_length=25,
            ),
        ),
        migrations.CreateModel(
            name="SupportNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("REQUEST_SUBMITTED", "Support Request Submitted"), ("REQUEST_RESUBMITTED", "Support Request Resubmitted"), ("DOCUMENTS_REQUIRED", "Additional Information / Documents Required"), ("REQUEST_APPROVED", "Support Request Approved")], db_index=True, max_length=40)),
                ("title", models.CharField(max_length=220)),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("support_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="support_requests.mosquesupportrequest")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "support notification",
                "verbose_name_plural": "support notifications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SupportNotificationDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(choices=[("EMAIL", "Email"), ("SMS", "SMS / Mobile")], max_length=10)),
                ("recipient", models.CharField(blank=True, max_length=254)),
                ("status", models.CharField(choices=[("SENT", "Sent"), ("FAILED", "Failed"), ("SKIPPED", "Skipped")], max_length=12)),
                ("provider", models.CharField(blank=True, max_length=160)),
                ("details", models.TextField(blank=True)),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="support_requests.supportnotification")),
            ],
            options={
                "verbose_name": "support notification delivery",
                "verbose_name_plural": "support notification deliveries",
                "ordering": ["-attempted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="supportnotification",
            index=models.Index(fields=["user", "is_read", "created_at"], name="support_notif_user_read_idx"),
        ),
    ]
