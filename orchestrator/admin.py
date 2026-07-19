from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models as django_models
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django_json_widget.widgets import JSONEditorWidget
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Conversation, KnowledgeBase, LLMConfig, Message, Prompt

User = get_user_model()


# ---------------------------------------------------------------------------
# LLM Config (singleton)
# ---------------------------------------------------------------------------
@admin.register(LLMConfig)
class LLMConfigAdmin(ModelAdmin):
    warn_unsaved_form = True
    fieldsets = (
        (
            "Model",
            {
                "description": "Which model to serve and build from.",
                "fields": (
                    "provider",
                    "base_model",
                    "wargaming_model",
                    "base_url",
                    "api_key",
                ),
            },
        ),
        (
            "Generation parameters",
            {
                "classes": ("tab",),
                "fields": (
                    "temperature",
                    "top_p",
                    "num_predict",
                    "num_ctx",
                    "repeat_penalty",
                    "conversation_history_limit",
                    "request_timeout_seconds",
                ),
            },
        ),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # There is only ever one config row: jump straight to it.
        obj = LLMConfig.load()
        return redirect(reverse("admin:orchestrator_llmconfig_change", args=[obj.pk]))


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
@admin.register(Prompt)
class PromptAdmin(ModelAdmin):
    warn_unsaved_form = True
    list_display = ("title", "key", "active_badge", "updated_at")
    list_filter = ("is_active", "key")
    search_fields = ("title", "content")
    readonly_fields = ("updated_at",)
    fields = ("key", "title", "is_active", "content", "updated_at")

    @display(description="Status", label={True: "success", False: "danger"})
    def active_badge(self, obj):
        return obj.is_active, ("Active" if obj.is_active else "Disabled")


# ---------------------------------------------------------------------------
# Knowledge datasets
# ---------------------------------------------------------------------------
@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(ModelAdmin):
    list_display = ("kind", "top_level_keys", "updated_at")
    readonly_fields = ("updated_at",)
    fields = ("kind", "data", "updated_at")
    formfield_overrides = {
        django_models.JSONField: {
            "widget": JSONEditorWidget(options={"mode": "tree", "modes": ["tree", "code"]})
        },
    }

    @display(description="Top-level sections")
    def top_level_keys(self, obj):
        if isinstance(obj.data, dict) and obj.data:
            keys = ", ".join(list(obj.data.keys())[:6])
            return keys
        return "—"


# ---------------------------------------------------------------------------
# Conversations & Messages
# ---------------------------------------------------------------------------
class MessageInline(TabularInline):
    model = Message
    extra = 0
    can_delete = False
    fields = ("role", "content", "created_at")
    readonly_fields = ("role", "content", "created_at")
    ordering = ("created_at",)
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    list_display = ("short_id", "message_count", "preview", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("id", "messages__content")
    readonly_fields = ("id", "created_at")
    inlines = (MessageInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_msg_count=Count("messages"))

    @display(description="Conversation")
    def short_id(self, obj):
        return f"#{str(obj.id)[:8]}"

    @display(description="Messages", ordering="_msg_count")
    def message_count(self, obj):
        return obj._msg_count

    @display(description="First message")
    def preview(self, obj):
        first = obj.messages.order_by("created_at").first()
        if not first:
            return "—"
        text = first.content[:70]
        return text + ("…" if len(first.content) > 70 else "")


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ("id", "conversation_link", "role_badge", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "conversation__id")
    date_hierarchy = "created_at"
    readonly_fields = ("conversation", "role", "content", "created_at")

    @display(description="Conversation")
    def conversation_link(self, obj):
        url = reverse("admin:orchestrator_conversation_change", args=[obj.conversation_id])
        return format_html('<a href="{}">#{}</a>', url, str(obj.conversation_id)[:8])

    @display(description="Role", label={"user": "info", "assistant": "success"})
    def role_badge(self, obj):
        return obj.role, obj.role.title()

    @display(description="Content")
    def short_content(self, obj):
        text = obj.content[:80]
        return text + ("…" if len(obj.content) > 80 else "")


# ---------------------------------------------------------------------------
# Re-register auth models with the Unfold look
# ---------------------------------------------------------------------------
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
