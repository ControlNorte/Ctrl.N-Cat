from django.contrib import admin
from .models import *

admin.site.register(BancosCliente)
admin.site.register(CategoriaMae)
admin.site.register(Categoria)
admin.site.register(SubCategoria)
admin.site.register(CentroDeCusto)
admin.site.register(MovimentacoesCliente)
admin.site.register(Regra)
admin.site.register(Saldo)
admin.site.register(UploadedFile)

# Register your models here.
