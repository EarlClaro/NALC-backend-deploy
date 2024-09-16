from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain_openai import OpenAI
import os
import time
from django.http import JsonResponse
from rest_framework.decorators import api_view
import json
from .models import researchpaper, Thread, Message, User
from .serializers import ThreadCreateSerializer
from rest_framework import generics, status
from .serializers import ThreadSerializer, MessageSerializer, UserCreateSerializer, UserLoginSerializer, UserSerializer, UserUpdateSerializer
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from django.core.paginator import Paginator



from django.db import connections
from django.utils.timezone import now

def get_openai_api_key():
    try:
        # Ensure you're connecting to the correct database schema (nalc_schema)
        with connections['default'].cursor() as cursor:
            # Execute the query to retrieve the API key from nalc_schema
            cursor.execute("""
                SELECT api_key FROM backend_openai_api WHERE id = 1
            """)
            row = cursor.fetchone()
            if row:
                print(f"API Key found: {row[0]}")
                return row[0]
            else:
                print("No entry found with id = 1.")
                return None
    except Exception as e:
        print(f"Error retrieving API key: {e}")
        return None

# Fetch and set the OpenAI API key from the Azure MySQL database (nalc_schema)
openai_api_key = get_openai_api_key()
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key
else:
    raise ValueError("OpenAI API key not found.")

# def get_openai_api_key():
#     try:
#         # Directly return the OpenAI API key
#         api_key = "sk-W90Ia71zv_mmq7LjqIo14KAof7iNvK-LnUIn8kqr51T3BlbkFJLg_cDgbK95ydsZXFO9aZ9bIg2NtDRse1mePtO9IhkA"  # Replace with your actual OpenAI API key
#         print(f"API Key found: {api_key}")
#         return api_key
#     except Exception as e:
#         print(f"Error retrieving API key: {e}")
#         return None

# # Fetch and set the OpenAI API key directly
# openai_api_key = get_openai_api_key()
# if openai_api_key:
#     os.environ["OPENAI_API_KEY"] = openai_api_key
# else:
#     raise ValueError("OpenAI API key not found.")

# Initialize OpenAI with the API key
llm = OpenAI(temperature=0, verbose=True)

# Create the SQLDatabase instance with the MySQL connection URI
# db = SQLDatabase.from_uri(f"mysql://{settings.DATABASES['default']['USER']}:{settings.DATABASES['default']['PASSWORD']}@{settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}/{settings.DATABASES['default']['NAME']}", include_tables=[])
db = SQLDatabase.from_uri(f"mysql://{settings.DATABASES['default']['USER']}:{settings.DATABASES['default']['PASSWORD'].replace('@', '%40')}@{settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}/{settings.DATABASES['default']['NAME']}", include_tables=[])


# connection_uri = f"mysql://{settings.DATABASES['default']['USER']}:{settings.DATABASES['default']['PASSWORD']}@{settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}/{settings.DATABASES['default']['NAME']}"
# print("Connection URI:", connection_uri)  # Add this to debug the URI
# db = SQLDatabase.from_uri(connection_uri, include_tables=[])

llm = OpenAI(temperature=0, verbose=True)

db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)





# Admin views
@csrf_exempt
def upload_and_replace_data(request):
    if 'file' in request.FILES:
        uploaded_file = request.FILES['file']
        if uploaded_file.name.endswith('.json'):
            try:
                with uploaded_file.open() as file:
                    data = json.load(file)
                    
                    # Clear existing data
                    researchpaper.objects.all().delete()

                    # Insert new data from the JSON file
                    total_rows = len(data)
                    chunk_size = 100
                    for i in range(0, total_rows, chunk_size):
                        chunk_data = data[i:i+chunk_size]
                        for item in chunk_data:

                            # Create the ResearchPaper object using the mapped values
                            researchpaper.objects.create(
                                title=item['Title'],
                                abstract=item['Abstract'],
                                year=item['Year'],
                                classification=item['Classification'],
                                author=item['Author'],
                                recommendations=item.get('Recommendations', '')  # New field added in the model
                            )
                        progress = int((i + chunk_size) / total_rows * 100)
                        if progress % 20 == 0:  # Send progress update every 20%
                            return JsonResponse({'progress': progress})

                    return JsonResponse({'message': 'Data replaced successfully.'})
            except Exception as e:
                return JsonResponse({'error': f'An error occurred while processing the file: {str(e)}'}, status=400)
        else:
            return JsonResponse({'error': 'Invalid file type. Only JSON files are accepted.'}, status=400)
    else:
        return JsonResponse({'error': 'No file provided in the request.'}, status=400)

    

# Thread Views (CRUD)
class ThreadListCreateView(generics.ListCreateAPIView):
    queryset = Thread.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ThreadCreateSerializer
        return ThreadSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"message": "Thread created", "data": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)

class ThreadDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Thread updated", "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Thread deleted"}, status=status.HTTP_204_NO_CONTENT)

class DeleteAllThreads(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        # Delete all threads associated with the user making the request
        Thread.objects.filter(user=request.user).delete()
        return Response({"message": "All threads deleted for the current user"}, status=status.HTTP_204_NO_CONTENT)

class UserThreadListView(generics.ListAPIView):
    serializer_class = ThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Retrieve the authenticated user based on the token
        user = self.request.user
        
        # Filter threads associated with the authenticated user
        queryset = Thread.objects.filter(user=user)
        return queryset

class MessageCreateView(generics.CreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        thread_id = request.data.get("thread_id")
        thread = get_object_or_404(Thread, pk=thread_id)

        query = request.data.get("query")

        # Fetch conversation history
        conversation_history = Message.objects.filter(thread=thread).order_by('created_at')
        history_text = "\n".join([json.loads(msg.message_text)['query'] + "\n" + json.loads(msg.message_text)['response'] for msg in conversation_history])

        # Combine history with the current query
        combined_query = history_text + "\nUser: " + query  # Make sure to label the speaker for clarity

        # Debug: print combined_query to check if history is correct
        print("Combined Query for db_chain:", combined_query)

        # Call db_chain with the combined_query to consider past conversation
        response = db_chain(combined_query)  # Assuming db_chain can handle this format

        # Debug: print response to check what db_chain returns
        print("Response from db_chain:", response)

        # Create a mutable copy of request.data
        mutable_data = request.data.copy()

        # Add the thread and message_text to the mutable_data
        mutable_data["thread"] = thread.pk

        # Structure the message_text for easy mapping in React
        message_text = {
            'query': query,
            'response': response.get("result", "No result found")
        }

        # Set the message_text field with the structured data
        mutable_data["message_text"] = json.dumps(message_text)

        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)

        # Save the new message
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response({"message": "Message created", "data": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get the thread_id from the URL parameter
        thread_id = self.kwargs.get('thread_id')
        
        # Retrieve all messages associated with the specified thread
        queryset = Message.objects.filter(thread_id=thread_id)
        return queryset

class UserRegisterView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', None)

        if email:
            if User.objects.filter(email=email).exists():
                # Email is already in use
                return Response({'error': 'Email is already in use.'}, status=status.HTTP_409_CONFLICT)

            serializer = self.get_serializer(data=request.data)
            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as validation_error:
                # Improper email format
                return Response({'error': 'Invalid email format.', 'details': validation_error.detail}, status=status.HTTP_400_BAD_REQUEST)

            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        # Invalid request, email is required
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

from .serializers import UserLoginSerializer

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)  # Only use email for login
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response_data = {
                'message': 'Login successful',
                'email': user.email,
                'name': user.name,
                'access_token': access_token,
                'is_superuser': user.is_superuser,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)


class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user  # Get the currently logged-in user

        serializer = UserUpdateSerializer(instance=user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserDetailsView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user 

