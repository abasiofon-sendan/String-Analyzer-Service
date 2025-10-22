from django.urls import path
from .views import (
    StringAnalysisView,
    SpecificStringview,
    NaturalLanguageFilterView,
)

urlpatterns = [
    path('strings', StringAnalysisView.as_view(), name='string-list-create'),
    path('strings/filter-by-natural-language', NaturalLanguageFilterView.as_view(), name='natural-filter'),
    path('strings/<str:string_value>', SpecificStringview.as_view(), name='string-detail'),
]
