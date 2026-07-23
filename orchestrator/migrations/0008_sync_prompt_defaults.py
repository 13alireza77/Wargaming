# Re-sync admin-editable Prompt rows with the current default prompt constants
# (UNIFIED_SYSTEM_PROMPT / DEFAULT_TRAINING_SYSTEM_PROMPT). Add one migration
# like this every time a default prompt changes so `migrate` updates DB + admin.

from django.core.management import call_command
from django.db import migrations


def sync_prompt_defaults(apps, schema_editor):
    call_command("seed_admin_data", force=True, prompts_only=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0007_persian_prompt_defaults"),
    ]

    operations = [
        migrations.RunPython(sync_prompt_defaults, noop_reverse),
    ]
