from django.urls import path, include
from cliente import views
from .views import *

app_name = 'cliente'

urlpatterns = [
    path('', Cliente.as_view(), name='cliente'),
    path('<int:pk>/', Destalhesclientes.as_view(), name='detalhesclientes'),
    path('cadastrarcliente/', cadastrarcliente, name='cadastrarcliente'),
    path('editar/<int:pk>/', Editarcliente.as_view(template_name='editarcliente.html'), name='editarcliente'),
    path('download_modelo_importacao/', views.download_modelo_importacao_cadastro_cliente, name='download_modelo_importacao_cadastro_cliente'),
]

