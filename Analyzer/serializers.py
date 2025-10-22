from rest_framework import serializers
from .models import String, StringProperties

class StringPropertiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = StringProperties
        fields = ['length', 'is_palindrome', 'word_count', 'string_hash', 'character_frequency_map']


class StringSerializer(serializers.ModelSerializer):
    properties = StringPropertiesSerializer(read_only=True)

    class Meta:
        model = String
        fields = ['id', 'value', 'properties','created_at']
