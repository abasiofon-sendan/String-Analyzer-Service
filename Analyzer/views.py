
import hashlib
import re
from collections import Counter

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import String, StringProperties
from .serializers import StringSerializer


class StringAnalysisView(APIView):
    """
    POST /strings  -> analyze & create
    GET  /strings  -> list with query filters
    """

    # ---------- POST /strings ----------
    def post(self, request):
        value = request.data.get("value", None)

        if value is None:
            return Response({"error": "Missing 'value' field"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(value, str):
            return Response({"error": "Invalid data type for 'value'. Must be a string."},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # compute SHA-256 hash
        sha256_hash = hashlib.sha256(value.encode()).hexdigest()

        # duplicate check
        if String.objects.filter(id=sha256_hash).exists():
            return Response({"error": "String already exists in the system."}, status=status.HTTP_409_CONFLICT)

        # compute properties
        normalized = value.lower().replace(" ", "")
        is_palindrome = normalized == normalized[::-1]
        length = len(value)
        word_count = len(value.split())
        character_frequency_map = dict(Counter(value))

        # create StringProperties and String atomically (simple approach)
        props = StringProperties.objects.create(
            length=length,
            is_palindrome=is_palindrome,
            word_count=word_count,
            string_hash=sha256_hash,
            character_frequency_map=character_frequency_map
        )

        string_instance = String.objects.create(
            id=sha256_hash,
            value=value,
            properties=props
        )

        response_data = {
            "id": string_instance.id,
            "value": string_instance.value,
            "properties": {
                "length": props.length,
                "is_palindrome": props.is_palindrome,
                "unique_characters": len(set(value)),
                "word_count": props.word_count,
                "sha256_hash": props.string_hash,
                "character_frequency_map": props.character_frequency_map,
            },
            "created_at": string_instance.created_at.isoformat(),
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    # ---------- GET /strings? ... ----------
    def get(self, request):
        query_params = request.query_params or {}
        filters_applied = {}

        # base queryset (use select_related for properties)
        queryset = String.objects.select_related("properties").all()

        # is_palindrome
        is_palindrome = query_params.get("is_palindrome")
        if is_palindrome is not None:
            if is_palindrome.lower() not in ("true", "false"):
                return Response({"error": "Invalid value for is_palindrome. Must be 'true' or 'false'."},
                                status=status.HTTP_400_BAD_REQUEST)
            val = True if is_palindrome.lower() == "true" else False
            queryset = queryset.filter(properties__is_palindrome=val)
            filters_applied["is_palindrome"] = val

        # min_length
        min_length = query_params.get("min_length")
        if min_length is not None:
            try:
                min_length_int = int(min_length)
            except (ValueError, TypeError):
                return Response({"error": "min_length must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(properties__length__gte=min_length_int)
            filters_applied["min_length"] = min_length_int

        # max_length
        max_length = query_params.get("max_length")
        if max_length is not None:
            try:
                max_length_int = int(max_length)
            except (ValueError, TypeError):
                return Response({"error": "max_length must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(properties__length__lte=max_length_int)
            filters_applied["max_length"] = max_length_int

        # word_count
        word_count = query_params.get("word_count")
        if word_count is not None:
            try:
                word_count_int = int(word_count)
            except (ValueError, TypeError):
                return Response({"error": "word_count must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(properties__word_count=word_count_int)
            filters_applied["word_count"] = word_count_int

        # contains_character
        contains_character = query_params.get("contains_character")
        if contains_character is not None:
            if not isinstance(contains_character, str) or len(contains_character) != 1:
                return Response({"error": "contains_character must be a single character."},
                                status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(value__icontains=contains_character)
            filters_applied["contains_character"] = contains_character

        serializer = StringSerializer(queryset, many=True)
        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "filters_applied": filters_applied
        }, status=status.HTTP_200_OK)


# ---------- GET /strings/<string_value>  and  DELETE ----------
class SpecificStringview(APIView):
    """
    Lookup strategy: try primary key (id), then value field.
    """

    def get_object(self, string_value):
        # prefer id (hash)
        obj = String.objects.filter(id=string_value).first()
        if obj:
            return obj
        # fallback to value match
        return String.objects.filter(value=string_value).first()

    def get(self, request, string_value):
        obj = self.get_object(string_value)
        if not obj:
            return Response({"error": "String does not exist in the system."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StringSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, string_value):
        obj = self.get_object(string_value)
        if not obj:
            return Response({"error": "String does not exist in the system."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- Natural Language Filtering ----------
class NaturalLanguageFilterView(APIView):
    """
    GET /strings/filter-by-natural-language?query=<text>
    Very basic parsing for the required patterns.
    """

    def get(self, request):
        query_text = request.query_params.get("query", "")
        if not query_text:
            return Response({"error": "Query parameter 'query' is required"}, status=status.HTTP_400_BAD_REQUEST)

        q = query_text.lower()
        parsed_filters = {}

        # palindromic
        if "palindrom" in q:  # handles 'palindrome' and 'palindromic'
            parsed_filters["is_palindrome"] = True

        # word count
        if "single word" in q or "one word" in q:
            parsed_filters["word_count"] = 1
        elif re.search(r'\btwo words\b', q):
            parsed_filters["word_count"] = 2
        else:
            # numeric word counts like "3-word" or "3 words"
            wc_match = re.search(r'(\d+)\s*(?:-|\s)?words?\b', q)
            if wc_match:
                parsed_filters["word_count"] = int(wc_match.group(1))

        # length matches
        longer_match = re.search(r'longer than (\d+)', q)
        if longer_match:
            parsed_filters["min_length"] = int(longer_match.group(1)) + 1

        shorter_match = re.search(r'shorter than (\d+)', q)
        if shorter_match:
            parsed_filters["max_length"] = int(shorter_match.group(1)) - 1

        # contains letter
        char_match = re.search(r'contain(?:ing)? the letter ([a-z])', q)
        if char_match:
            parsed_filters["contains_character"] = char_match.group(1)
        elif "contain the first vowel" in q:
            parsed_filters["contains_character"] = "a"

        if not parsed_filters:
            return Response({"error": "Unable to parse natural language query"}, status=status.HTTP_400_BAD_REQUEST)

        # build queryset from parsed_filters
        queryset = String.objects.select_related("properties").all()
        if "is_palindrome" in parsed_filters:
            queryset = queryset.filter(properties__is_palindrome=parsed_filters["is_palindrome"])
        if "word_count" in parsed_filters:
            queryset = queryset.filter(properties__word_count=parsed_filters["word_count"])
        if "min_length" in parsed_filters:
            queryset = queryset.filter(properties__length__gte=parsed_filters["min_length"])
        if "max_length" in parsed_filters:
            queryset = queryset.filter(properties__length__lte=parsed_filters["max_length"])
        if "contains_character" in parsed_filters:
            queryset = queryset.filter(value__icontains=parsed_filters["contains_character"])

        serializer = StringSerializer(queryset, many=True)
        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "interpreted_query": {
                "original": query_text,
                "parsed_filters": parsed_filters
            }
        }, status=status.HTTP_200_OK)






            
       
            


