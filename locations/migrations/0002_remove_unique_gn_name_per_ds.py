from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="gndivision",
            name="unique_gn_name_per_ds",
        ),
    ]
