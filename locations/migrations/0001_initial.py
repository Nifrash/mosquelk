from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Province",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name_en", models.CharField(max_length=120)),
                ("name_ta", models.CharField(blank=True, max_length=120)),
                ("name_ar", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "province",
                "verbose_name_plural": "provinces",
                "ordering": ["name_en"],
            },
        ),
        migrations.CreateModel(
            name="District",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name_en", models.CharField(max_length=120)),
                ("name_ta", models.CharField(blank=True, max_length=120)),
                ("name_ar", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("province", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="districts", to="locations.province")),
            ],
            options={
                "verbose_name": "district",
                "verbose_name_plural": "districts",
                "ordering": ["name_en"],
            },
        ),
        migrations.CreateModel(
            name="DivisionalSecretariat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30, unique=True)),
                ("name_en", models.CharField(max_length=160)),
                ("name_ta", models.CharField(blank=True, max_length=160)),
                ("name_ar", models.CharField(blank=True, max_length=160)),
                ("is_active", models.BooleanField(default=True)),
                ("district", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="divisional_secretariats", to="locations.district")),
            ],
            options={
                "verbose_name": "divisional secretariat",
                "verbose_name_plural": "divisional secretariats",
                "ordering": ["name_en"],
            },
        ),
        migrations.CreateModel(
            name="GNDivision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("name_en", models.CharField(max_length=180)),
                ("name_ta", models.CharField(blank=True, max_length=180)),
                ("name_ar", models.CharField(blank=True, max_length=180)),
                ("is_active", models.BooleanField(default=True)),
                ("divisional_secretariat", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="gn_divisions", to="locations.divisionalsecretariat")),
            ],
            options={
                "verbose_name": "GN division",
                "verbose_name_plural": "GN divisions",
                "ordering": ["name_en"],
            },
        ),
        migrations.CreateModel(
            name="DistrictOfficerAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("district", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="officer_assignments", to="locations.district")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="district_assignment", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "district officer assignment",
                "verbose_name_plural": "district officer assignments",
                "ordering": ["district__name_en", "user__username"],
            },
        ),
        migrations.AddConstraint(
            model_name="district",
            constraint=models.UniqueConstraint(fields=("province", "name_en"), name="unique_district_name_per_province"),
        ),
        migrations.AddConstraint(
            model_name="divisionalsecretariat",
            constraint=models.UniqueConstraint(fields=("district", "name_en"), name="unique_ds_name_per_district"),
        ),
        migrations.AddConstraint(
            model_name="gndivision",
            constraint=models.UniqueConstraint(fields=("divisional_secretariat", "name_en"), name="unique_gn_name_per_ds"),
        ),
    ]
