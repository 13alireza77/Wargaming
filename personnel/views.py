import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .services.personnel_service import PersonnelService

logger = logging.getLogger(__name__)

# Initialize the personnel service
personnel_service = PersonnelService()

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for personnel service"""
    try:
        # Test if personnel data is loaded
        countries = personnel_service.get_available_countries()
        
        return JsonResponse({
            "status": "healthy",
            "service": "personnel",
            "available_countries": len(countries),
            "message": "Personnel service is operational"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            "status": "unhealthy",
            "service": "personnel",
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_countries(request):
    """Get list of available countries"""
    try:
        countries = personnel_service.get_available_countries()
        
        return JsonResponse({
            "success": True,
            "countries": countries,
            "count": len(countries)
        })
    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_country_personnel(request, country):
    """Get personnel data for a specific country"""
    try:
        result = personnel_service.get_country_personnel(country)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except Exception as e:
        logger.error(f"Error getting country personnel: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_branch_personnel(request, country, branch):
    """Get personnel data for a specific branch of a country"""
    try:
        result = personnel_service.get_branch_personnel(country, branch)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except Exception as e:
        logger.error(f"Error getting branch personnel: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_branches(request, country=None):
    """Get available branches for a country or all countries"""
    try:
        result = personnel_service.get_available_branches(country)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=404)
            
    except Exception as e:
        logger.error(f"Error getting branches: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_personnel(request):
    """Analyze personnel data based on query"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        country = data.get('country')
        branch = data.get('branch')
        
        if not query:
            return JsonResponse({
                "success": False,
                "error": "Query is required"
            }, status=400)
        
        result = personnel_service.analyze_personnel(query, country, branch)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        logger.error(f"Error analyzing personnel: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def calculate_victory_probability(request):
    """Calculate victory probability between two countries"""
    try:
        data = json.loads(request.body)
        country1 = data.get('country1', '')
        country2 = data.get('country2', '')
        scenario = data.get('scenario', 'conventional')
        
        if not country1 or not country2:
            return JsonResponse({
                "success": False,
                "error": "Both country1 and country2 are required"
            }, status=400)
        
        result = personnel_service.calculate_victory_probability(country1, country2, scenario)
        
        if result["success"]:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        logger.error(f"Error calculating victory probability: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_personnel_summary(request):
    """Get summary of all personnel data"""
    try:
        countries = personnel_service.get_available_countries()
        summary = {}
        
        for country in countries:
            country_data = personnel_service.get_country_personnel(country)
            if country_data["success"]:
                data = country_data["data"]
                summary[country] = {
                    "name": data.get("name"),
                    "total_personnel": data.get("total_personnel"),
                    "active_duty": data.get("active_duty"),
                    "reserves": data.get("reserves"),
                    "branches": list(data.get("branches", {}).keys())
                }
        
        return JsonResponse({
            "success": True,
            "summary": summary,
            "total_countries": len(summary)
        })
        
    except Exception as e:
        logger.error(f"Error getting personnel summary: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
