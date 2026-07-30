# Re-seed KnowledgeBase rows after expanding personnel + weapons JSON coverage
# (missing countries, air defense, missiles, helicopters, naval, APC/IFV, anti-tank).

from django.core.management import call_command
from django.db import migrations


def sync_knowledge_datasets(apps, schema_editor):
    call_command("seed_admin_data", force=True, knowledge_only=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0011_battle_structure_no_duplicates"),
    ]

    operations = [
        migrations.RunPython(sync_knowledge_datasets, noop_reverse),
    ]
