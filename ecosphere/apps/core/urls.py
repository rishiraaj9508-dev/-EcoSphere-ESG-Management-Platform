from django.urls import path
from .views import DepartmentListView, CategoryListView, ESGConfigurationUpdateView

app_name = 'core'

urlpatterns = [
    path('departments/', DepartmentListView.as_view(), name='departments'),
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('esg-config/', ESGConfigurationUpdateView.as_view(), name='esg-config'),
]
