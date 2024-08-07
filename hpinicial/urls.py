from django.urls import path, reverse_lazy
from .views import Perfil, Criarconta, Editarperfil
from django.contrib.auth import views as auth_view

app_name = 'homepageinicial'

urlpatterns = [
    path('login/', auth_view.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_view.LogoutView.as_view(template_name='logged_out.html'), name='logout'),
    path('perfil/<int:pk>', Perfil.as_view(template_name='perfil.html'), name='perfil'),
    path('criarconta/', Criarconta.as_view(template_name='criarconta.html'), name='criarconta'),
    path('editarperfil/<int:pk>', Editarperfil.as_view(template_name='editarperfil.html'), name='editarperfil'),
    path('mudarsenha/', auth_view.PasswordChangeView.as_view(template_name='editarperfil.html',
                                                             success_url=reverse_lazy('financeiro:financeiro')
                                                             ), name='mudarsenha'),
]