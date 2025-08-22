from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from .services.weapons_service import WeaponsService

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_weapons(request):
    """
    API endpoint for weapons analysis
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        weapon_category = data.get('weapon_category', None)
        country = data.get('country', None)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)
        
        # Initialize weapons service
        weapons_service = WeaponsService()
        
        # Check if model is available
        if not weapons_service.check_model_availability():
            return JsonResponse({
                'success': False,
                'error': 'LLM model not available. Please ensure Ollama is running and the model is installed.'
            }, status=503)
        
        # Perform analysis
        result = weapons_service.analyze_weapons(query, weapon_category, country)
        
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
        logger.error(f"Error in analyze_weapons: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def get_weapon_categories(request):
    """
    API endpoint to get list of available weapon categories
    """
    try:
        weapons_service = WeaponsService()
        categories = weapons_service.get_available_weapon_categories()
        
        return JsonResponse({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        logger.error(f"Error in get_weapon_categories: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def get_weapon_category_data(request, category):
    """
    API endpoint to get data for a specific weapon category
    """
    try:
        weapons_service = WeaponsService()
        category_data = weapons_service.get_weapon_category_data(category)
        
        if category_data:
            return JsonResponse({
                'success': True,
                'category': category,
                'data': category_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Weapon category "{category}" not found'
            }, status=404)
    except Exception as e:
        logger.error(f"Error in get_weapon_category_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def get_country_weapons(request, country):
    """
    API endpoint to get all weapons data for a specific country
    """
    try:
        weapons_service = WeaponsService()
        country_weapons = weapons_service.get_country_weapons(country)
        
        if country_weapons:
            return JsonResponse({
                'success': True,
                'country': country,
                'weapons': country_weapons
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'No weapons data found for country "{country}"'
            }, status=404)
    except Exception as e:
        logger.error(f"Error in get_country_weapons: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def calculate_victory_probability(request):
    """
    API endpoint to calculate victory probability between two countries
    """
    try:
        data = json.loads(request.body)
        country1 = data.get('country1', '')
        country2 = data.get('country2', '')
        scenario = data.get('scenario', 'conventional')
        
        if not country1 or not country2:
            return JsonResponse({
                'success': False,
                'error': 'Both country1 and country2 are required'
            }, status=400)
        
        # Initialize weapons service
        weapons_service = WeaponsService()
        
        # Check if model is available
        if not weapons_service.check_model_availability():
            return JsonResponse({
                'success': False,
                'error': 'LLM model not available. Please ensure Ollama is running and the model is installed.'
            }, status=503)
        
        # Calculate victory probability
        result = weapons_service.calculate_victory_probability(country1, country2, scenario)
        
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
        logger.error(f"Error in calculate_victory_probability: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def weapons_health_check(request):
    """
    Health check endpoint to verify weapons service status
    """
    try:
        weapons_service = WeaponsService()
        model_available = weapons_service.check_model_availability()
        
        return JsonResponse({
            'success': True,
            'llm_available': model_available,
            'model_name': weapons_service.model_name,
            'available_categories': len(weapons_service.get_available_weapon_categories())
        })
    except Exception as e:
        logger.error(f"Error in weapons_health_check: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Health check failed: {str(e)}'
        }, status=500)
