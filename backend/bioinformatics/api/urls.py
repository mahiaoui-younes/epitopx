"""
URL configuration for MSA API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MSAViewSet, MSAHealthView

router = DefaultRouter()
router.register(r'', MSAViewSet, basename='msa')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', MSAHealthView.as_view(), name='msa-health'),
]
