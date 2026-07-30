from django.test import TestCase

from orchestrator.models import Conversation, Message
from orchestrator.services.orchestrator_service import OrchestratorService
from orchestrator.services.router import Router
from war_game.project_config import UNIFIED_LLM_GENERATION_CONFIG

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

    def test_air_defense_question_detects_air_defense_subtype(self):
        intent = self.router.route("Compare Iran and Israel air defense systems")

        self.assertEqual(intent["focus"], ["weapons"])
        self.assertIn("air_defense", intent["weapon_subtypes"])

    def test_persian_air_defense_keyword_is_detected(self):
        intent = self.router.route("پدافند هوایی ایران و اسرائیل را مقایسه کن")

        self.assertIn("air_defense", intent["weapon_subtypes"])
        self.assertEqual(intent["countries"], ["iran", "israel"])


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

    def test_air_defense_context_includes_systems_and_specs(self):
        context = self.service._build_context_block(
            {
                "countries": ["iran", "israel"],
                "scenario": "conventional",
                "message_type": "comparison",
                "focus": ["weapons"],
                "weapon_subtypes": ["air_defense"],
                "processed_message": "Compare Iran and Israel air defense.",
            }
        )

        self.assertIn("Air Defense Systems", context)
        self.assertIn("iron_dome", context)
        self.assertIn("bavar_373", context)
        self.assertIn("range=", context)
        self.assertNotIn("no specific data found for air defense", context.lower())

    def test_personnel_context_covers_syria(self):
        context = self.service._build_context_block(
            {
                "countries": ["syria"],
                "scenario": "conventional",
                "message_type": "question",
                "focus": ["personnel"],
                "processed_message": "Advise on Syria personnel.",
            }
        )

        self.assertIn("Personnel:", context)
        self.assertIn("Syria:", context)
        self.assertIn("total", context)

    def test_generation_options_use_project_defaults(self):
        options = _generation_options_for_intent(
            {
                "message_type": "greeting",
                "focus": ["general"],
                "countries": [],
            }
        )

        self.assertEqual(options["num_predict"], UNIFIED_LLM_GENERATION_CONFIG["num_predict"])
        self.assertEqual(options["num_ctx"], UNIFIED_LLM_GENERATION_CONFIG["num_ctx"])

    def test_generation_options_are_consistent_across_intents(self):
        greeting_options = _generation_options_for_intent(
            {
                "message_type": "greeting",
                "focus": ["general"],
                "countries": [],
            }
        )
        comparison_options = _generation_options_for_intent(
            {
                "message_type": "comparison",
                "focus": ["weapons"],
                "countries": ["iran", "israel"],
            }
        )

        self.assertEqual(greeting_options, comparison_options)


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


class DocumentKnowledgeTestCase(TestCase):
    def test_txt_extract_and_chunking(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from orchestrator.models import KnowledgeDocument
        from orchestrator.services.document_ingest import chunk_text, detect_file_type, ingest_document

        self.assertEqual(detect_file_type("briefing.txt"), "txt")
        with self.assertRaises(Exception):
            detect_file_type("notes.xlsx")

        long_body = ("Iran coastal defense note. " * 40) + "\n\n" + ("Israel air doctrine. " * 40)
        chunks = chunk_text(long_body, chunk_size=200, overlap=40)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(len(c) <= 240 for c in chunks))

        upload = SimpleUploadedFile(
            "iran_brief.txt",
            b"Iran has 120 coastal patrol boats in this classified annex.",
            content_type="text/plain",
        )
        doc = KnowledgeDocument.objects.create(
            title="Iran brief",
            file=upload,
            file_type="txt",
        )
        ingest_document(doc)
        doc.refresh_from_db()
        self.assertEqual(doc.status, KnowledgeDocument.Status.READY)
        self.assertGreater(doc.char_count, 0)
        self.assertGreaterEqual(doc.chunk_count, 1)
        self.assertIn("120 coastal patrol", doc.extracted_text)
        self.assertEqual(doc.chunks.count(), doc.chunk_count)

    def test_retriever_ranks_country_matching_chunk_higher(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from orchestrator.models import KnowledgeDocument
        from orchestrator.services.document_ingest import ingest_document
        from orchestrator.services.document_retriever import retrieve_document_chunks

        iran_upload = SimpleUploadedFile(
            "iran.txt",
            b"Iran operates the Fateh-110 ballistic missile with extended range variants.",
            content_type="text/plain",
        )
        other_upload = SimpleUploadedFile(
            "unrelated.txt",
            b"Generic logistics checklist for warehouse inventory and packing labels.",
            content_type="text/plain",
        )
        iran_doc = KnowledgeDocument.objects.create(title="Iran missiles", file=iran_upload, file_type="txt")
        other_doc = KnowledgeDocument.objects.create(title="Logistics", file=other_upload, file_type="txt")
        ingest_document(iran_doc)
        ingest_document(other_doc)

        results = retrieve_document_chunks(
            query="What ballistic missiles does Iran have?",
            countries=["iran"],
            top_k=5,
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["title"], "Iran missiles")
        self.assertIn("Fateh-110", results[0]["content"])

    def test_context_block_includes_uploaded_document_excerpts(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from orchestrator.models import KnowledgeDocument
        from orchestrator.services.document_ingest import ingest_document
        from orchestrator.services.unified_llm_service import UnifiedLLMService

        upload = SimpleUploadedFile(
            "syria_note.txt",
            b"Syria maintains fortified positions along the Golan approaches with layered artillery.",
            content_type="text/plain",
        )
        doc = KnowledgeDocument.objects.create(title="Syria Golan note", file=upload, file_type="txt")
        ingest_document(doc)

        service = UnifiedLLMService()
        context = service._build_context_block(
            {
                "countries": ["syria"],
                "scenario": "conventional",
                "message_type": "question",
                "focus": ["geography"],
                "processed_message": "Describe Syria defenses near Golan.",
            },
            query="Describe Syria defenses near Golan.",
        )
        self.assertIn("Uploaded documents:", context)
        self.assertIn("Syria Golan note", context)
        self.assertIn("Golan", context)

    def test_inactive_documents_are_not_retrieved(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from orchestrator.models import KnowledgeDocument
        from orchestrator.services.document_ingest import ingest_document
        from orchestrator.services.document_retriever import retrieve_document_chunks

        upload = SimpleUploadedFile(
            "secret.txt",
            b"Iran secret force multiplier XYZ-99 is mentioned only here.",
            content_type="text/plain",
        )
        doc = KnowledgeDocument.objects.create(
            title="Secret",
            file=upload,
            file_type="txt",
            is_active=False,
        )
        ingest_document(doc)
        results = retrieve_document_chunks(query="Iran XYZ-99", countries=["iran"])
        self.assertEqual(results, [])

    def test_delete_removes_uploaded_file_from_disk(self):
        import os

        from django.conf import settings
        from django.core.files.uploadedfile import SimpleUploadedFile

        from orchestrator.models import KnowledgeDocument

        upload = SimpleUploadedFile(
            "delete_me.txt",
            b"This file should be removed when the document is deleted.",
            content_type="text/plain",
        )
        doc = KnowledgeDocument.objects.create(title="Delete me", file=upload, file_type="txt")
        file_path = os.path.join(settings.MEDIA_ROOT, doc.file.name)
        self.assertTrue(os.path.isfile(file_path))

        KnowledgeDocument.objects.filter(pk=doc.pk).delete()
        self.assertFalse(os.path.isfile(file_path))
