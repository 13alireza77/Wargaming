# Switch default base model to gemma3:12b and GPU-oriented generation limits.

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
                default="gemma3:12b",
                help_text="Base model used when (re)building the custom wargaming model.",
                max_length=120,
            ),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="num_predict",
            field=models.IntegerField(default=800, help_text="Max tokens to generate."),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="num_ctx",
            field=models.IntegerField(default=8192, help_text="Context window size."),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="request_timeout_seconds",
            field=models.IntegerField(default=300),
        ),
    ]
