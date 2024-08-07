from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11)