from django.contrib import admin
from .models import *

class Historicoadmin(admin.ModelAdmin):
    list_display = ['name', 'descricao']

# Register your models here.
admin.site.register(cadastro_de_cliente)
admin.site.register(Ramo)

