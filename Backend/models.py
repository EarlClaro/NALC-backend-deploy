from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(blank=True, default='', unique=True, max_length=255)
    name = models.CharField(max_length=255, blank=True, default='')

    # Subscription field without choices
    subscription = models.CharField(max_length=255, default='FREE TRIAL')  # Default subscription set to FREE

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email
        
    def get_full_name(self):
        return self.name

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserMessageLog(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    message_count = models.IntegerField(default=0)
    last_reset = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - Messages sent: {self.message_count}"



class researchpaper(models.Model):
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    year = models.IntegerField()
    record_type_choices = (
        ('1-Proposal', 'Proposal'),
        ('2-Thesis/Research', 'Thesis/Research'),
        ('3-Project', 'Project'),
    )
    record_type = models.CharField(max_length=100, choices=record_type_choices)
    classification_choices = (
        (1, 'Basic Research'),
        (2, 'Applied Research'),
    )
    classification = models.IntegerField(choices=classification_choices)
    author = models.CharField(max_length=255)
    recommendations = models.TextField(blank=True)

    def __str__(self):
        return self.title




class Thread(models.Model):
    thread_id = models.AutoField(primary_key=True)
    thread_name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='threads')

class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

from django.db import models, connections

class BackendOpenAIAPI(models.Model):
    api_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'backend_openai_api'
        managed = False  # No migrations will be created for this model
