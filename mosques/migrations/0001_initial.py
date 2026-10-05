# Generated for Phase 4 - Mosque Registration System
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import mosques.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("locations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Mosque",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mosque_id", models.CharField(blank=True, db_index=True, editable=False, max_length=24, null=True, unique=True)),
                ("name_en", models.CharField(max_length=220, verbose_name="Mosque name (English)")),
                ("name_ta", models.CharField(blank=True, max_length=220, verbose_name="Mosque name (Tamil)")),
                ("name_ar", models.CharField(blank=True, max_length=220, verbose_name="Mosque name (Arabic)")),
                ("category", models.CharField(choices=[("JUMMA", "Jumma Mosque"), ("MASJID", "Mosque / Masjid"), ("MUSALLA", "Musalla / Prayer Hall"), ("OTHER", "Other")], default="MASJID", max_length=20)),
                ("established_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("existing_registration_number", models.CharField(blank=True, max_length=100)),
                ("address_line1", models.CharField(max_length=220)),
                ("address_line2", models.CharField(blank=True, max_length=220)),
                ("city_or_town", models.CharField(max_length=120)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("official_phone", models.CharField(max_length=30)),
                ("alternate_phone", models.CharField(blank=True, max_length=30)),
                ("official_email", models.EmailField(blank=True, max_length=254)),
                ("website", models.URLField(blank=True)),
                ("description_en", models.TextField(blank=True, verbose_name="Description (English)")),
                ("description_ta", models.TextField(blank=True, verbose_name="Description (Tamil)")),
                ("description_ar", models.TextField(blank=True, verbose_name="Description (Arabic)")),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("NEEDS_CHANGES", "Changes Required"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], db_index=True, default="DRAFT", max_length=25)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_mosque_applications", to=settings.AUTH_USER_MODEL)),
                ("district", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mosques", to="locations.district")),
                ("divisional_secretariat", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="mosques", to="locations.divisionalsecretariat")),
                ("gn_division", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="mosques", to="locations.gndivision")),
                ("province", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mosques", to="locations.province")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_mosque_applications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "mosque",
                "verbose_name_plural": "mosques",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "district"], name="mosque_status_district_idx"),
                    models.Index(fields=["name_en"], name="mosque_name_en_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="MosqueCommitteeMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=180)),
                ("designation", models.CharField(choices=[("PRESIDENT", "President / Chairman"), ("SECRETARY", "Secretary"), ("TREASURER", "Treasurer"), ("TRUSTEE", "Trustee"), ("IMAM", "Imam"), ("MUEZZIN", "Muezzin"), ("MEMBER", "Committee Member"), ("OTHER", "Other")], default="MEMBER", max_length=20)),
                ("phone_number", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("is_primary_contact", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="committee_members", to="mosques.mosque")),
            ],
            options={"ordering": ["designation", "full_name"]},
        ),
        migrations.CreateModel(
            name="MosqueDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(choices=[("REGISTRATION", "Existing Registration Certificate"), ("COMMITTEE", "Committee Authorization / Letter"), ("LAND", "Land / Property Document"), ("BUILDING", "Building / Construction Document"), ("PHOTO", "Mosque Photograph"), ("OTHER", "Other Supporting Document")], default="OTHER", max_length=30)),
                ("title", models.CharField(max_length=180)),
                ("file", models.FileField(upload_to=mosques.models.mosque_document_upload_to)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="mosques.mosque")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="uploaded_mosque_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MosqueMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("membership_role", models.CharField(choices=[("ADMIN", "Mosque Admin"), ("STAFF", "Mosque Staff")], default="STAFF", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("added_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="added_mosque_memberships", to=settings.AUTH_USER_MODEL)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="mosques.mosque")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mosque_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["mosque__name_en", "user__username"]},
        ),
        migrations.CreateModel(
            name="MosqueReviewHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("NEEDS_CHANGES", "Changes Required"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], max_length=25)),
                ("to_status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("NEEDS_CHANGES", "Changes Required"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], max_length=25)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="review_history", to="mosques.mosque")),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mosque_review_actions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "mosque review history",
                "verbose_name_plural": "mosque review history",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="mosquemembership",
            constraint=models.UniqueConstraint(fields=("mosque", "user"), name="unique_user_membership_per_mosque"),
        ),
    ]
