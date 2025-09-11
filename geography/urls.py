from django.urls import path
from . import views

app_name = 'geography'

urlpatterns = [
    path('api/analyze/', views.analyze_geography, name='analyze_geography'),
    path('api/war-conditions/', views.analyze_war_conditions, name='analyze_war_conditions'),
    path('api/regions/', views.get_available_regions, name='get_available_regions'),
    path('api/regions/<str:region>/', views.get_region_data, name='get_region_data'),
    path('api/health/', views.health_check, name='health_check'),
]
