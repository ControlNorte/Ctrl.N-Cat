from django.urls import path, include
from cliente import views
from .views import Cliente, Destalhesclientes, Editarcliente, cadastrarcliente

app_name = 'cliente'

urlpatterns = [
    path('', Cliente.as_view(), name='cliente'),
    path('<int:pk>/', Destalhesclientes.as_view(), name='detalhesclientes'),
    path('cadastrarcliente/', cadastrarcliente, name='cadastrarcliente'),
    path('editar/<int:pk>/', Editarcliente.as_view(template_name='editarcliente.html'), name='editarcliente'),
]

