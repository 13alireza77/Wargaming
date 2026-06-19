from django.test import TestCase

from orchestrator.models import Conversation, Message
from orchestrator.services.orchestrator_service import OrchestratorService
from orchestrator.services.router import Router
from orchestrator.services.unified_llm_service import UnifiedLLMService, _generation_options_for_intent


class RouterTestCase(TestCase):
    def setUp(self):
        self.router = Router()

    def test_greeting_message_is_detected(self):
        intent = self.router.route("hello")

        self.assertEqual(intent["message_type"], "greeting")
        self.assertEqual(intent["countries"], [])
        self.assertIn("greeting", intent["processed_message"].lower())

    def test_country_comparison_is_detected(self):
        intent = self.router.route("Compare Iran and Israel for a conventional war")

        self.assertEqual(intent["message_type"], "comparison")
        self.assertEqual(intent["countries"], ["iran", "israel"])
        self.assertEqual(intent["country_pair"], ["iran", "israel"])
        self.assertEqual(intent["scenario"], "conventional")
        self.assertIn("side-by-side", intent["processed_message"].lower())

    def test_battle_advice_is_detected(self):
        intent = self.router.route("Give me battle advice for Syria in mountain warfare")

        self.assertEqual(intent["message_type"], "battle_advice")
        self.assertEqual(intent["countries"], ["syria"])
        self.assertEqual(intent["scenario"], "mountain")
        self.assertIn("battle advice", intent["processed_message"].lower())

    def test_air_fighter_question_detects_fighter_jet_subtype(self):
        intent = self.router.route("Can you compare Iran and Israel air fighters?")

        self.assertEqual(intent["message_type"], "comparison")
        self.assertEqual(intent["focus"], ["weapons"])
        self.assertEqual(intent["weapon_subtypes"], ["fighter_jets"])


class UnifiedLLMContextTestCase(TestCase):
    def setUp(self):
        self.service = UnifiedLLMService()

    def test_context_block_uses_only_requested_domain_summary_without_default_countries(self):
        context = self.service._build_context_block(
            {
                "countries": [],
                "scenario": "conventional",
                "message_type": "question",
                "focus": ["weapons"],
                "processed_message": "Answer a weapons question.",
            }
        )

        self.assertIn("Weapons:", context)
        self.assertNotIn("Geography:", context)
        self.assertNotIn("Personnel:", context)
        self.assertNotIn("Israel:", context)
        self.assertNotIn("Iran:", context)

    def test_context_block_uses_requested_country_without_adding_other_countries(self):
        context = self.service._build_context_block(
            {
                "countries": ["syria"],
                "scenario": "mountain",
                "message_type": "battle_advice",
                "focus": ["geography"],
                "processed_message": "Assess Syria in mountain warfare.",
            }
        )

        self.assertIn("Geography:", context)
        self.assertIn("Syria:", context)
        self.assertNotIn("Personnel:", context)
        self.assertNotIn("Weapons:", context)
        self.assertNotIn("Israel:", context)

    def test_air_fighter_context_is_filtered_to_fighter_jets(self):
        context = self.service._build_context_block(
            {
                "countries": ["iran", "israel"],
                "scenario": "conventional",
                "message_type": "comparison",
                "focus": ["weapons"],
                "weapon_subtypes": ["fighter_jets"],
                "processed_message": "Compare Iran and Israel air fighters.",
            }
        )

        self.assertIn("Fighter Jets", context)
        self.assertNotIn("Assault Rifles", context)
        self.assertNotIn("Sniper Rifles", context)
        self.assertNotIn("Anthrax", context)
        self.assertNotIn("Nerve Agents", context)
        self.assertNotIn("Fission Weapons", context)

    def test_generation_options_are_trimmed_for_greetings(self):
        options = _generation_options_for_intent(
            {
                "message_type": "greeting",
                "focus": ["general"],
                "countries": [],
            }
        )

        self.assertEqual(options["num_predict"], 80)
        self.assertLessEqual(options["num_ctx"], 3072)

    def test_generation_options_limit_comparison_output(self):
        options = _generation_options_for_intent(
            {
                "message_type": "comparison",
                "focus": ["weapons"],
                "countries": ["iran", "israel"],
            }
        )

        self.assertEqual(options["num_predict"], 260)
        self.assertEqual(options["num_ctx"], 3072)


class OrchestratorConversationContextTestCase(TestCase):
    def test_recent_conversation_context_prefers_latest_messages(self):
        conversation = Conversation.objects.create()
        for index in range(12):
            Message.objects.create(
                conversation=conversation,
                role="user" if index % 2 == 0 else "assistant",
                content=f"message-{index}",
            )

        service = OrchestratorService()
        context = service._get_conversation_context(str(conversation.id))

        self.assertEqual(len(context), 10)
        self.assertEqual(context[0]["content"], "message-2")
        self.assertEqual(context[-1]["content"], "message-11")
