from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ArticleViewSet,
    DNASequenceViewSet,
    ProteinConversionViewSet,
    ProteinViewSet,
    EpitopeAnalysisViewSet,
    UserViewSet,
    BioinformaticsViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'articles', ArticleViewSet)
router.register(r'dna', DNASequenceViewSet)
router.register(r'proteins', ProteinViewSet, basename='protein')
router.register(r'conversions', ProteinConversionViewSet, basename='conversion')
router.register(r'epitopes', EpitopeAnalysisViewSet, basename='epitope')
router.register(r'bio', BioinformaticsViewSet, basename='bio')

urlpatterns = [
    path('', include(router.urls)),
]
