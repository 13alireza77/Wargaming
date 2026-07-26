# Re-sync Prompt rows after tightening the battle-scenario structure rules
# (each heading once; no bare player->country duplicate lines).

from django.core.management import call_command
from django.db import migrations


def sync_prompt_defaults(apps, schema_editor):
    call_command("seed_admin_data", force=True, prompts_only=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0010_consultant_prompt_wording"),
    ]

    operations = [
        migrations.RunPython(sync_prompt_defaults, noop_reverse),
    ]
