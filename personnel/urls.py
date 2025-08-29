from django.urls import path
from . import views

app_name = 'personnel'

urlpatterns = [
    # Health check
    path('api/health/', views.health_check, name='health_check'),
    
    # Data retrieval endpoints
    path('api/countries/', views.get_countries, name='get_countries'),
    path('api/countries/<str:country>/personnel/', views.get_country_personnel, name='get_country_personnel'),
    path('api/countries/<str:country>/branches/<str:branch>/personnel/', views.get_branch_personnel, name='get_branch_personnel'),
    path('api/branches/', views.get_branches, name='get_branches'),
    path('api/countries/<str:country>/branches/', views.get_branches, name='get_country_branches'),
    path('api/summary/', views.get_personnel_summary, name='get_personnel_summary'),
    
    # Analysis endpoints
    path('api/analyze/', views.analyze_personnel, name='analyze_personnel'),
    path('api/victory-probability/', views.calculate_victory_probability, name='calculate_victory_probability'),
]
