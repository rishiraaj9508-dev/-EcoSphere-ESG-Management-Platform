from django.urls import path
from .views import (
    EmissionFactorListView, EmissionFactorCreateView, EmissionFactorUpdateView,
    CarbonEmissionListView, CarbonEmissionCreateView, CarbonEmissionUpdateView,
    SustainabilityGoalListView, SustainabilityGoalCreateView, SustainabilityGoalUpdateView,
    EnvironmentalDashboardView
)

app_name = 'environmental'

urlpatterns = [
    # Carbon Emissions tracking
    path('emissions/', CarbonEmissionListView.as_view(), name='emissions'),
    path('emissions/add/', CarbonEmissionCreateView.as_view(), name='emission-add'),
    path('emissions/<int:pk>/edit/', CarbonEmissionUpdateView.as_view(), name='emission-edit'),
    
    # Emission Factors CRUD
    path('factors/add/', EmissionFactorCreateView.as_view(), name='factor-add'),
    path('factors/<int:pk>/edit/', EmissionFactorUpdateView.as_view(), name='factor-edit'),
    
    # Sustainability Goals CRUD
    path('goals/', SustainabilityGoalListView.as_view(), name='goals'),
    path('goals/add/', SustainabilityGoalCreateView.as_view(), name='goal-add'),
    path('goals/<int:pk>/edit/', SustainabilityGoalUpdateView.as_view(), name='goal-edit'),
    
    # Environmental Dashboard
    path('dashboard/', EnvironmentalDashboardView.as_view(), name='dashboard'),
]
