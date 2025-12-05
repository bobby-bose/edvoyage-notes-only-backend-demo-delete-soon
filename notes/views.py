# api/views.py

from rest_framework import viewsets
from .models import Subject, Doctor, Video, MCQ, Question, Option , ClinicalCase , Flashcard , FlashcardImage , Category
from rest_framework import serializers
from .serializers import SubjectSerializer, DoctorSerializer, VideoSerializer, MCQSerializer, QuestionSerializer, OptionSerializer , ClinicalCaseSerializer , FlashcardSerializer , CategorySerializer
from rest_framework import viewsets

from django.http import FileResponse, Http404
from django.conf import settings
import os

def media_serve(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        raise Http404

    response = FileResponse(open(file_path, "rb"))
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "*"
    return response


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer



class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows subjects to be viewed.
    Provides `list` and `retrieve` actions.
    """
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows doctors to be viewed.
    Provides `list` and `retrieve` actions.
    """
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows videos to be viewed.
    Provides `list` and `retrieve` actions.
    Can be filtered by subject or doctor ID, e.g., /api/videos/?subject=1
    """
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    filterset_fields = ['subject', 'doctor', 'is_free', 'category']


class MCQViewSet(viewsets.ModelViewSet):
    queryset = MCQ.objects.all()
    serializer_class = MCQSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class OptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.all()
    serializer_class = OptionSerializer



class ClinicalCaseViewSet(viewsets.ModelViewSet):
    # Use select_related to perform a SQL join and improve performance
    queryset = ClinicalCase.objects.select_related('doctor').all()
    serializer_class = ClinicalCaseSerializer


class FlashcardViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Flashcard.objects.all().order_by('id')
    serializer_class = FlashcardSerializer