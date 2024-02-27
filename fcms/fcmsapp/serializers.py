from rest_framework import serializers
from fcmsapp.models import *

class CustomUserSerializer(serializers.ModelSerializer):
     class Meta:
          model = CustomUser
          fields = '__all__'

class CaseSerializer(serializers.ModelSerializer):
     class Meta:
          model = Case
          fields = '__all__'

class EvidenceSerializer(serializers.ModelSerializer):
     case = CaseSerializer(read_only=False)

     class Meta:
          model = Evidence
          fields = '__all__'

class AnalysisResultSerializer(serializers.ModelSerializer):
     evidence = EvidenceSerializer(read_only=False)

     class Meta:
          model = AnalysisResult
          fields = '__all__'

class StaffSerializer(serializers.ModelSerializer):
     user = CustomUserSerializer(read_only=False)

     class Meta:
          model = Staff
          fields = '__all__'

class CorpseSerializer(serializers.ModelSerializer):
     case = CaseSerializer(read_only=False)
     staff = StaffSerializer(read_only=False)

     class Meta:
          model = Corpse
          fields = '__all__'