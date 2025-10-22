from django.db import models

class StringProperties(models.Model):
    length = models.IntegerField()
    is_palindrome = models.BooleanField(default=False)
    word_count = models.IntegerField()
    string_hash = models.CharField(max_length=500)
    character_frequency_map = models.JSONField()

class String(models.Model):
    id = models.CharField(max_length=500, primary_key=True)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    properties = models.OneToOneField(
        StringProperties,
        on_delete=models.CASCADE,
        related_name='string',
        null=True,
        blank=True
    )
