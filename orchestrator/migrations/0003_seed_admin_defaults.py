# Align LLMConfig field defaults with project_config and seed admin-editable rows.

from django.core.management import call_command
from django.db import migrations, models


def seed_admin_defaults(apps, schema_editor):
    # Force so fresh servers (and rows created by visiting admin early) get
    # the same prompts / config / knowledge as a seeded local install.
    call_command("seed_admin_data", force=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0002_knowledgebase_llmconfig_prompt"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconfig",
            name="base_model",
            field=models.CharField(
                default="gemma3:4b",
                help_text="Base model used when (re)building the custom wargaming model.",
                max_length=120,
            ),
        ),
        migrations.AlterField(
            model_name="llmconfig",
            name="num_predict",
            field=models.IntegerField(default=600, help_text="Max tokens to generate."),
        ),
        migrations.RunPython(seed_admin_defaults, noop_reverse),
    ]
