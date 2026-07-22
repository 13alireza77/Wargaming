# Push the updated Persian wargaming prompts into admin-editable defaults.

from django.core.management import call_command
from django.db import migrations


def seed_persian_prompt_defaults(apps, schema_editor):
    call_command("seed_admin_data", force=True, prompts_only=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0006_gemma3_12b_gpu_defaults"),
    ]

    operations = [
        migrations.RunPython(seed_persian_prompt_defaults, noop_reverse),
    ]
