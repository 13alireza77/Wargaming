# Re-sync Prompt rows after rebranding the assistant voice from
# "analyst / تحلیل" to "consultant / مشاور / مشاوره".

from django.core.management import call_command
from django.db import migrations


def sync_prompt_defaults(apps, schema_editor):
    call_command("seed_admin_data", force=True, prompts_only=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0009_sync_prompt_defaults"),
    ]

    operations = [
        migrations.RunPython(sync_prompt_defaults, noop_reverse),
    ]
