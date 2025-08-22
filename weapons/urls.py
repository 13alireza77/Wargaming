from django.urls import path
from . import views

app_name = 'weapons'

urlpatterns = [
    path('api/analyze/', views.analyze_weapons, name='analyze_weapons'),
    path('api/categories/', views.get_weapon_categories, name='get_weapon_categories'),
    path('api/categories/<str:category>/', views.get_weapon_category_data, name='get_weapon_category_data'),
    path('api/countries/<str:country>/weapons/', views.get_country_weapons, name='get_country_weapons'),
    path('api/victory-probability/', views.calculate_victory_probability, name='calculate_victory_probability'),
    path('api/health/', views.weapons_health_check, name='weapons_health_check'),
]
