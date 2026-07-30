from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import KnowledgeDocument


@receiver(pre_delete, sender=KnowledgeDocument)
def remove_knowledge_document_file(sender, instance, **kwargs):
    """Remove uploaded file from storage when a document row is deleted."""
    if instance.file and instance.file.name:
        instance.file.delete(save=False)
