# Switch default base model to gemma3n:e2b and restore fuller generation limits.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0004_faster_cpu_llm_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconfig",
            name="base_model",
            field=models.CharField(
                default="gemma3n:e2b",
                help_text="Base model used when (re)building the custom wargaming model.",
                max_length=120,
            ),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="num_predict",
            field=models.IntegerField(default=450, help_text="Max tokens to generate."),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="num_ctx",
            field=models.IntegerField(default=3072, help_text="Context window size."),
        ),
    ]
