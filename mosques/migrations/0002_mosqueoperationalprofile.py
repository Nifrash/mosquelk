from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mosques", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MosqueOperationalProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_phone", models.CharField(blank=True, max_length=30)),
                ("whatsapp_number", models.CharField(blank=True, max_length=30)),
                ("public_email", models.EmailField(blank=True, max_length=254)),
                ("imam_name", models.CharField(blank=True, max_length=180)),
                ("muezzin_name", models.CharField(blank=True, max_length=180)),
                ("jummah_prayer_time", models.TimeField(blank=True, null=True)),
                ("capacity_men", models.PositiveIntegerField(blank=True, null=True)),
                ("capacity_women", models.PositiveIntegerField(blank=True, null=True)),
                ("has_womens_prayer_area", models.BooleanField(default=False)),
                ("has_parking", models.BooleanField(default=False)),
                ("wheelchair_accessible", models.BooleanField(default=False)),
                ("has_wudu_facilities", models.BooleanField(default=True)),
                ("has_madrasa", models.BooleanField(default=False)),
                ("public_summary_en", models.TextField(blank=True, verbose_name="Public summary (English)")),
                ("public_summary_ta", models.TextField(blank=True, verbose_name="Public summary (Tamil)")),
                ("public_summary_ar", models.TextField(blank=True, verbose_name="Public summary (Arabic)")),
                ("facebook_url", models.URLField(blank=True)),
                ("youtube_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("mosque", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="operational_profile", to="mosques.mosque")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_mosque_operational_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "mosque operational profile",
                "verbose_name_plural": "mosque operational profiles",
            },
        ),
    ]
