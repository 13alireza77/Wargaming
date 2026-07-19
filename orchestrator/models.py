import uuid

from django.db import models


class SingletonModel(models.Model):
    """Base model that always resolves to a single row (pk=1)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Deleting the singleton is a no-op; there must always be one config row.
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class LLMConfig(SingletonModel):
    """Runtime configuration for the LLM service. Editable from the admin."""

    class Provider(models.TextChoices):
        OLLAMA = "ollama", "Ollama"
        CITOME = "citome", "Citome"
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OLLAMA,
        help_text="Which LLM backend to use.",
    )
    base_url = models.CharField(
        max_length=255,
        default="http://localhost:11434",
        help_text="Base URL of the LLM backend.",
    )
    base_model = models.CharField(
        max_length=120,
        default="gemma3n:e2b",
        help_text="Base model used when (re)building the custom wargaming model.",
    )
    wargaming_model = models.CharField(
        max_length=120,
        default="wargaming:unified",
        help_text="Model name served at inference time.",
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="API key for hosted providers (leave blank for local Ollama).",
    )

    # Generation parameters
    temperature = models.FloatField(default=0.4)
    top_p = models.FloatField(default=0.9)
    num_predict = models.IntegerField(default=450, help_text="Max tokens to generate.")
    num_ctx = models.IntegerField(default=3072, help_text="Context window size.")
    repeat_penalty = models.FloatField(default=1.1)
    conversation_history_limit = models.IntegerField(
        default=2,
        help_text="How many previous messages to include as context.",
    )
    request_timeout_seconds = models.IntegerField(default=180)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LLM Config"
        verbose_name_plural = "LLM Config"

    def __str__(self):
        return f"{self.get_provider_display()} · {self.wargaming_model}"


class Prompt(models.Model):
    """Editable system prompts used by the service."""

    class Key(models.TextChoices):
        UNIFIED_SYSTEM = "unified_system", "Runtime system prompt"
        TRAINING_SYSTEM = "training_system", "Training system prompt"

    key = models.CharField(max_length=50, choices=Key.choices, unique=True)
    title = models.CharField(max_length=120)
    content = models.TextField(help_text="The full prompt text.")
    is_active = models.BooleanField(
        default=True,
        help_text="If disabled, the built-in default prompt is used instead.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.title or self.get_key_display()


class KnowledgeBase(models.Model):
    """One record per knowledge domain, storing the full JSON dataset."""

    class Kind(models.TextChoices):
        GEOGRAPHY = "geography", "Geography"
        PERSONNEL = "personnel", "Personnel"
        WEAPONS = "weapons", "Weapons"

    kind = models.CharField(max_length=20, choices=Kind.choices, unique=True)
    data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind"]
        verbose_name = "Knowledge dataset"
        verbose_name_plural = "Knowledge datasets"

    def __str__(self):
        return self.get_kind_display()


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Conversation {str(self.id)[:8]}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)  # 'user' or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
