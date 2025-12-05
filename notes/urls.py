# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, DoctorViewSet, VideoViewSet , MCQViewSet, QuestionViewSet, OptionViewSet , ClinicalCaseViewSet , FlashcardViewSet , CategoryViewSet





# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'subjects', SubjectViewSet)
router.register(r'doctors', DoctorViewSet)
router.register(r'videos', VideoViewSet)
router.register(r'mcqs', MCQViewSet)
router.register(r'questions', QuestionViewSet)
router.register(r'options', OptionViewSet)
router.register(r'clinical-cases', ClinicalCaseViewSet)
router.register(r'flashcards', FlashcardViewSet, basename='flashcard')
router.register(r'categories', CategoryViewSet)


urlpatterns = [
    path('', include(router.urls)),
]