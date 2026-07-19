# Switch default base model to qwen2.5:3b (lighter, CPU-friendly, usable Persian).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0005_gemma3n_e2b_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconfig",
            name="base_model",
            field=models.CharField(
                default="qwen2.5:3b",
                help_text="Base model used when (re)building the custom wargaming model.",
                max_length=120,
            ),
        ),
    ]
