from django.urls import path
from .views import (
    CSRActivityListView, CSRActivityCreateView, CSRActivityUpdateView,
    CSRActivityEnrolView, CSRParticipationSubmitView, CSRParticipationApproveView,
    CSRParticipationRejectView, DiversityMetricListView, TrainingListView
)

app_name = 'social'

urlpatterns = [
    # CSR Activities
    path('csr/', CSRActivityListView.as_view(), name='csr'),
    path('csr/add/', CSRActivityCreateView.as_view(), name='csr-add'),
    path('csr/<int:pk>/edit/', CSRActivityUpdateView.as_view(), name='csr-edit'),
    path('csr/<int:pk>/enrol/', CSRActivityEnrolView.as_view(), name='csr-enrol'),
    path('csr/participation/<int:pk>/submit/', CSRParticipationSubmitView.as_view(), name='csr-submit'),
    path('csr/participation/<int:pk>/approve/', CSRParticipationApproveView.as_view(), name='csr-approve'),
    path('csr/participation/<int:pk>/reject/', CSRParticipationRejectView.as_view(), name='csr-reject'),
    
    # Stubs for clean routing
    path('diversity/', DiversityMetricListView.as_view(), name='diversity'),
    path('training/', TrainingListView.as_view(), name='training'),
]
