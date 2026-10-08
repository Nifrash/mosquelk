from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SMSOTPChallenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(db_index=True, max_length=30)),
                ("purpose", models.CharField(choices=[
                    ("ACCOUNT_REGISTRATION", "Account Registration"),
                    ("MOSQUE_SUBMISSION", "Mosque Registration Submission"),
                    ("SUPPORT_SUBMISSION", "Support Request Submission"),
                ], db_index=True, max_length=40)),
                ("target_reference", models.CharField(blank=True, db_index=True, max_length=160)),
                ("code_hash", models.CharField(max_length=255)),
                ("session_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("send_count", models.PositiveSmallIntegerField(default=1)),
                ("last_sent_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.CharField(blank=True, max_length=160)),
                ("last_delivery_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="sms_otp_challenges", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "SMS OTP challenge",
                "verbose_name_plural": "SMS OTP challenges",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="smsotpchallenge",
            index=models.Index(fields=["phone_number", "purpose", "created_at"], name="accounts_otp_phone_purpose_idx"),
        ),
        migrations.AddIndex(
            model_name="smsotpchallenge",
            index=models.Index(fields=["user", "purpose", "consumed_at"], name="accounts_otp_user_purpose_idx"),
        ),
    ]
