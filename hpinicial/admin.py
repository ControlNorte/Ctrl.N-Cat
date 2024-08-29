from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
# Register your models here.

campos = list(UserAdmin.fieldsets)
campos.append(("Informações pessoais", {"fields":("cpf", "tenant")}))

UserAdmin.fieldsets = tuple(campos)

admin.site.register(Usuario, UserAdmin)
admin.site.register(Tenant)
