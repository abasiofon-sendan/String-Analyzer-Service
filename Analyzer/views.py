import hashlib
from collections import Counter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import String, StringProperties
from .serializers import StringSerializer


class StringAnalysisView(APIView):
    def post(self, request):

        value = request.data.get("value")
        if value is None:
            return Response(
                {"error": "Missing 'value' field"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(value, str):
            return Response(
                {"error": "Invalid data type for 'value'. Must be a string."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        sha256_hash = hashlib.sha256(value.encode()).hexdigest()
        if String.objects.filter(id=sha256_hash).exists():
            return Response(
                {"error": "String already exists in the system."},
                status=status.HTTP_409_CONFLICT
            )

        normalized = value.lower().replace(" ", "")
        is_palindrome = normalized == normalized[::-1]
        length = len(value)
        word_count = len(value.split())
        character_frequency_map = dict(Counter(value))

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
                "word_count": props.word_count,
                "sha256_hash": props.string_hash,
                "character_frequency_map": props.character_frequency_map,
            },
            "created_at": string_instance.created_at.isoformat(),
        }

        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def get(self,request):
        data= String.objects.all()
        serilaizer=StringSerializer(data,many=True)
        query_params = request.query_params
        filters_applied ={}

        #filter all
        query_set = String.objects.select_related('properties')

        # filter by is_palindrome
        is_palindrome = query_params.get('is_palindrome')
        
        if is_palindrome is not None:
            if is_palindrome.lower() not in ['true','false']:
                return Response(
                    {"error":"Invalid value for is_palindrome. Must be 'true' or 'false'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            value=True if is_palindrome.lower()=='true' else False
            query_set = query_set.filter(properties__is_palindrome=value)
            filters_applied['is_palindrome']=value

         

        # filter by min_length   

        min_length = query_params.get('min_length')
        if min_length is not None:
            try:
                min_length = int(min_length)
            except ValueError:
                return Response(
                    {"error":"Invalid value for min_length. Must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            query_set = query_set.filter(properties__length__gte=int(min_length))
            filters_applied['max_length']=min_length

        #filter by max_length

        max_length= query_params.get('max_length')
        try:
            if not max_length.isdigit():
                return Response({"error":"min_length must be an integer"},status=status.HTTP_400_BAD_REQUEST)
            query_set = query_set.filter(properties__length__lte=int(max_length))
            filters_applied['max_length']=int(max_length)
        except AttributeError :
            return Response(serilaizer.data,status=status.HTTP_200_OK)

        # filter by word_count
        word_count = query_params.get('word_count')
        if word_count is not None:
            if not word_count.isdigit():
                return Response({"error":"word_count must be an integer"},status=status.HTTP_400_BAD_REQUEST)
            query_set=query_set.filter(properties__word_count=int(word_count))
            filters_applied['word_count']=int(word_count)
                

            # contains_character
        contains_character = query_params.get("contains_character")
        if contains_character is not None:
            if len(contains_character) != 1:
                return Response({"error": "contains_character must be a single character."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = query_set.filter(value__icontains=contains_character)
            filters_applied["contains_character"] = contains_character


        serilaizer = StringSerializer(query_set,many=True)
        response_data= {
            "data":serilaizer.data,
            "count":query_set.count(),
            "filters_applied":filters_applied
        }
        return Response(response_data,status=status.HTTP_200_OK)



class SpecificStringview(APIView):
        def get(self, request,string_value):
            try:
                string= String.objects.get(value=string_value)
            except String.DoesNotExist:
                return Response({"error":"String does not exist in the system"}, status=status.HTTP_404_NOT_FOUND)
            serializer = StringSerializer(string)
            return Response(serializer.data, status=status.HTTP_200_OK)

        def delete(self,request,string_value):
            try:
                string=String.objects.get(value=string_value)
            except:
                return Response({"error":"String does not exist in the system"},status=status.HTTP_404_NOT_FOUND)
            string.delete()
            return Response({"message":"No Content"},status=status.HTTP_204_NO_CONTENT)


class NaturalLanguageFilterView(APIView):
    def get(self, request):
        query_params = request.query_params.get("query", "")
        parsed_filters = {}

        if not query_params:
            return Response({"error": "Query parameter 'query' is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Keyword checks
        if "palindrome" in query_params:
            parsed_filters["is_palindrome"] = True

        if "single word" in query_params or "one word" in query_params:
            parsed_filters["word_count"] = 1
        elif "two words" in query_params:
            parsed_filters["word_count"] = 2

        import re

        longer_match = re.search(r'longer than (\d+)', query_params)
        shorter_match = re.search(r'shorter than (\d+)', query_params)

        if longer_match:
            parsed_filters["min_length"] = int(longer_match.group(1)) + 1
        if shorter_match:
            parsed_filters["max_length"] = int(shorter_match.group(1)) - 1

        char_match = re.search(r'contain(?:ing)? the letter ([a-z])', query_params)
        if char_match:
            parsed_filters["contains_character"] = char_match.group(1)
        elif "contain the first vowel" in query_params:
            parsed_filters["contains_character"] = "a"

        # Querying the database
        query_set = String.objects.all()

        if "is_palindrome" in parsed_filters:
            query_set = query_set.filter(properties__is_palindrome=parsed_filters["is_palindrome"])
        if "word_count" in parsed_filters:
            query_set = query_set.filter(properties__word_count=parsed_filters["word_count"])
        if "min_length" in parsed_filters:
            query_set = query_set.filter(properties__length__gte=parsed_filters["min_length"])
        if "max_length" in parsed_filters:
            query_set = query_set.filter(properties__length__lte=parsed_filters["max_length"])
        if "contains_character" in parsed_filters:
            query_set = query_set.filter(value__icontains=parsed_filters["contains_character"])

        data = [
            {
                "id": s.id,
                "value": s.value,
                "created_at": s.created_at,
                "properties": {
                    "length": s.properties.length,
                    "is_palindrome": s.properties.is_palindrome,
                    "word_count": s.properties.word_count,
                    "string_hash": s.properties.string_hash,
                    "character_frequency_map": s.properties.character_frequency_map,
                },
            }
            for s in query_set
        ]

        return Response({
            "data": data,
            "count": len(data),
            "interpreted_query": {
                "original": query_params,
                "parsed_filters": parsed_filters
            }
        }, status=status.HTTP_200_OK)
     







            
       
            


