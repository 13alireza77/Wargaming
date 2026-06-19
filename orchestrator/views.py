from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from .services.orchestrator_service import OrchestratorService

logger = logging.getLogger(__name__)


def chat_view(request):
    """Serve the chat UI page."""
    return render(request, 'orchestrator/chat.html')


@csrf_exempt
@require_http_methods(['POST'])
def chat_api(request):
    """
    Chat API: POST with { "message": "...", "conversation_id": "uuid" }.
    Returns { "reply": "...", "sources": [...], "conversation_id": "..." }.
    """
    try:
        data = json.loads(request.body) if request.body else {}
        message = (data.get('message') or '').strip()
        conversation_id = data.get('conversation_id')

        if not message:
            return JsonResponse({
                'success': False,
                'error': 'message is required',
            }, status=400)

        service = OrchestratorService()
        result = service.process_message(message, conversation_id=conversation_id)

        if not result.get('success'):
            return JsonResponse(result, status=500)

        return JsonResponse({
            'success': True,
            'reply': result['reply'],
            'sources': result.get('sources', []),
            'conversation_id': result.get('conversation_id'),
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception('chat_api error')
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)
