from django.urls import path
from .views import ConceptMapView

urlpatterns = [
    path('', ConceptMapView.as_view(), name='concept_map'),
]