# api/serializers.py

from rest_framework import serializers
from .models import Subject, Doctor, Video , MCQ, Question, Option , ClinicalCase , Flashcard , FlashcardImage , Category



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class SubjectSerializer(serializers.ModelSerializer):
    # Calculates how many videos are in each subject
    video_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'video_count']

    def get_video_count(self, obj):
        return obj.videos.count()

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name']

class VideoSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    # Nests the full doctor object in the video response instead of just an ID
    doctor = DoctorSerializer(read_only=True)
    # Shows the subject's name for easier display on the frontend
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'category',
            'video_url',
            'logo',
          
            'is_free',
            'subject', # The subject's ID
            'subject_name', # The subject's name
            'doctor' # The nested doctor object
        ]


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'mcq', 'options']


class MCQSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = MCQ
        fields = ['id', 'title', 'subject', 'is_free', 'logo', 'questions', 'category']


class ClinicalCaseSerializer(serializers.ModelSerializer):
    """
    Serializer for the ClinicalCase model.
    """
    
    # Use StringRelatedField to show the name of the doctor/subject
    # instead of just their ID. This is read-only.
    category = CategorySerializer(read_only=True)
    doctor_name = serializers.StringRelatedField(source='doctor', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    
    class Meta:
        model = ClinicalCase
        # List all fields you want to include in the API
        fields = [
            'id',
            'case_title',
            'doctor',
            'doctor_name',
            'subject_name',
            'category',
            
            'gather_equipments',
            'introduction',
            'general_inspection',
            'closer_inspection',
            'palpation',
            'final_examination',
            'references',
            'created_at',
            'updated_at',
        ]
        # Make the ForeignKey fields writeable for creating/updating instances
        extra_kwargs = {
            'doctor': {'write_only': True},
           
        }
# In your app's serializers.py file



class FlashcardImageSerializer(serializers.ModelSerializer):
    """
    Serializer for the FlashcardImage model.
    """
    class Meta:
        model = FlashcardImage
        fields = ['id', 'image', 'caption']


class FlashcardSerializer(serializers.ModelSerializer):
    """
    Serializer for the main Flashcard model, including its nested images
    and related subject information.
    """
    # Nested serializer for images remains the same
    images = FlashcardImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    sub_subject_name = serializers.StringRelatedField(
        source='sub_subject',read_only=True)
    
    # Provides the string representation of the subject (e.g., "Anatomy") for reading.
    subject_name = serializers.StringRelatedField(source='subject', read_only=True)

    class Meta:
        model = Flashcard
        # Updated fields: 'title' is removed, 'subject' and 'subject_name' are added.
        fields = [
            'id',
            'subject', # Used for writing (expects a subject ID)
            'subject_name', # Used for reading
            'sub_subject',
            'sub_subject_name',
            'category',
            'description',
            'created_at',
            'images',
        ]
        extra_kwargs = {
            'subject': {'write_only': True}
        }