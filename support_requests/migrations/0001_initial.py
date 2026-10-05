from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import support_requests.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mosques", "0002_mosqueoperationalprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="MosqueSupportRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_no", models.CharField(blank=True, db_index=True, editable=False, max_length=30, null=True, unique=True)),
                ("category", models.CharField(choices=[("MOSQUE_ISSUE", "General Mosque Issue"), ("CONSTRUCTION", "Construction"), ("RENOVATION", "Renovation / Repair"), ("SALARY", "Imam / Muezzin / Staff Salary"), ("UTILITIES", "Water / Electricity / Utilities"), ("MAINTENANCE", "Maintenance"), ("EQUIPMENT", "Furniture / Equipment"), ("FINANCIAL", "Financial Assistance"), ("EDUCATION", "Religious / Educational Program"), ("EMERGENCY", "Emergency Assistance"), ("OTHER", "Other")], db_index=True, max_length=30)),
                ("priority", models.CharField(choices=[("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")], db_index=True, default="NORMAL", max_length=15)),
                ("title", models.CharField(max_length=220)),
                ("issue_description", models.TextField(verbose_name="Describe the issue / current situation")),
                ("requested_support", models.TextField(verbose_name="Support requested")),
                ("requested_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="Requested amount (LKR)")),
                ("contact_person", models.CharField(max_length=180)),
                ("contact_phone", models.CharField(max_length=30)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("DOCUMENTS_REQUIRED", "Documents Required"), ("APPROVED", "Approved"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="DRAFT", max_length=25)),
                ("approved_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="Approved amount (LKR)")),
                ("latest_admin_note", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_support_requests", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_support_requests", to=settings.AUTH_USER_MODEL)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="support_requests", to="mosques.mosque")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_support_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "mosque support request",
                "verbose_name_plural": "mosque support requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SupportRequestDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("file", models.FileField(upload_to=support_requests.models.support_document_upload_to)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("support_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="support_requests.mosquesupportrequest")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="uploaded_support_request_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SupportRequestHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("DOCUMENTS_REQUIRED", "Documents Required"), ("APPROVED", "Approved"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], max_length=25)),
                ("to_status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("UNDER_REVIEW", "Under Review"), ("DOCUMENTS_REQUIRED", "Documents Required"), ("APPROVED", "Approved"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], max_length=25)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="support_request_actions", to=settings.AUTH_USER_MODEL)),
                ("support_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="history", to="support_requests.mosquesupportrequest")),
            ],
            options={
                "verbose_name": "support request history",
                "verbose_name_plural": "support request history",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mosquesupportrequest",
            index=models.Index(fields=["status", "priority"], name="support_status_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="mosquesupportrequest",
            index=models.Index(fields=["mosque", "status"], name="support_mosque_status_idx"),
        ),
        migrations.AddIndex(
            model_name="mosquesupportrequest",
            index=models.Index(fields=["category"], name="support_category_idx"),
        ),
    ]
