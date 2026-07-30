from django.core.management import call_command
from django.db import migrations


def sync_prompt_defaults(apps, schema_editor):
    call_command("seed_admin_data", force=True, prompts_only=True)


class Migration(migrations.Migration):
    dependencies = [
        ("orchestrator", "0013_knowledge_documents"),
    ]

    operations = [
        migrations.RunPython(sync_prompt_defaults, migrations.RunPython.noop),
    ]
