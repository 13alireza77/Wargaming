from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .services.llm_service import LLMService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def analyze_geography(request):
    """
    API endpoint for geographical analysis
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        region = data.get('region', None)

        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)

        # Initialize LLM service
        llm_service = LLMService()

        # Check if model is available
        if not llm_service.check_model_availability():
            return JsonResponse({
                'success': False,
                'error': 'LLM model not available. Please ensure Ollama is running and the model is installed.'
            }, status=503)

        # Perform analysis
        result = llm_service.analyze_geography(query, region)

        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in analyze_geography: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_available_regions(request):
    """
    API endpoint to get list of available regions
    """
    try:
        llm_service = LLMService()
        regions = llm_service.get_available_regions()

        return JsonResponse({
            'success': True,
            'regions': regions
        })
    except Exception as e:
        logger.error(f"Error in get_available_regions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_region_data(request, region):
    """
    API endpoint to get data for a specific region
    """
    try:
        llm_service = LLMService()
        region_data = llm_service.get_region_data(region)

        if region_data:
            return JsonResponse({
                'success': True,
                'region': region,
                'data': region_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Region "{region}" not found'
            }, status=404)
    except Exception as e:
        logger.error(f"Error in get_region_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def analyze_war_conditions(request):
    """
    API endpoint for war conditions analysis between two regions
    """
    try:
        data = json.loads(request.body)
        attacker_region = data.get('attacker_region', '')
        defender_region = data.get('defender_region', '')
        scenario = data.get('scenario', None)

        if not attacker_region or not defender_region:
            return JsonResponse({
                'success': False,
                'error': 'Both attacker_region and defender_region are required'
            }, status=400)

        # Initialize LLM service
        llm_service = LLMService()

        # Check if model is available
        if not llm_service.check_model_availability():
            return JsonResponse({
                'success': False,
                'error': 'LLM model not available. Please ensure Ollama is running and the model is installed.'
            }, status=503)

        # Perform war conditions analysis
        result = llm_service.analyze_war_conditions(attacker_region, defender_region, scenario)

        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in analyze_war_conditions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint to verify LLM service status
    """
    try:
        llm_service = LLMService()
        model_available = llm_service.check_model_availability()

        return JsonResponse({
            'success': True,
            'llm_available': model_available,
            'model_name': llm_service.model_name,
            'available_regions': len(llm_service.get_available_regions())
        })
    except Exception as e:
        logger.error(f"Error in health_check: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Health check failed: {str(e)}'
        }, status=500)
