# Generated by Django 5.0.1 on 2024-02-07 16:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Backend", "0002_researchpaper_recommendations_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="researchpaper",
            name="recommendations",
            field=models.TextField(blank=True, default=""),
        ),
    ]
