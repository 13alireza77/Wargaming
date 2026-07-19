# Faster CPU-oriented LLMConfig field defaults.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0003_seed_admin_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconfig",
            name="num_predict",
            field=models.IntegerField(default=280, help_text="Max tokens to generate."),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="num_ctx",
            field=models.IntegerField(default=2048, help_text="Context window size."),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="conversation_history_limit",
            field=models.IntegerField(
                default=2,
                help_text="How many previous messages to include as context.",
            ),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="request_timeout_seconds",
            field=models.IntegerField(default=180),
        ),
    ]
