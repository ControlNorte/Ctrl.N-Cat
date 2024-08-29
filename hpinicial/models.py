from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class Tenant(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    subdomain = models.CharField(max_length=255, unique=True)
    cnpj = models.IntegerField(unique=True)
    ativo = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.nome


class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11)
