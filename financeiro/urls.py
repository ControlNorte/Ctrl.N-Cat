from django.urls import path, re_path
from . import views
from .views import *
# from django.contrib.auth import views as auth_view

app_name = 'financeiro'

urlpatterns = [
    path('', Financeiro.as_view(), name='financeiro'),
    path('financeirocliente/<int:pk>/', financeirocliente, name='financeirocliente'),

    path('financeirocliente/caixa/', caixa, name='caixa'),
    path('financeirocliente/movimentacao/<str:banco>', movimentacao, name='movimentacao'),

    path('financeirocliente/dre/', dre, name='dre'),
    path('financeirocliente/dashboard/', dashboard, name='dashboard'),

    path('financeirocliente/orcamento/', orcamento, name='orcamento'),
    path('financeirocliente/orcamento/cadastrar', cadastrarorcamento, name='cadastrarorcamento'),

    path('financeirocliente/contas/', contas, name='contas'),


    path('financeirocliente/maisopicoes/', maisopicoes, name='maisopicoes'),

    path('financeirocliente/maisopicoes/banco/', banco, name='banco'),
    path('financeirocliente/maisopicoes/banco/editar/<int:pk>', editarbanco, name='editarbanco'),
    path('financeirocliente/maisopicoes/banco/saldo/<int:pk>', bancosaldo, name='bancosaldo'),

    path('financeirocliente/maisopicoes/categoria/', categoria, name='categoria'),
    path('financeirocliente/maisopicoes/categoria/editar/<int:pk>', editarcategoria, name='editarcategoria'),

    path('financeirocliente/maisopicoes/subcategoria/', subcategoria, name='subcategoria'),
    path('financeirocliente/maisopicoes/subcategoria/editar/<int:pk>', editarsubcategoria, name='editarsubcategoria'),

    path('financeirocliente/maisopicoes/centrocusto/', centrocusto, name='centrocusto'),
    path('financeirocliente/maisopicoes/centrocusto/editar/<int:pk>', editarcentrocusto, name='editarcentrocusto'),

    path('financeirocliente/maisopicoes/regra/', regra, name='regra'),
    path('financeirocliente/maisopicoes/regra/editar/<int:pk>', editarregra, name='editarregra'),

    path('save-data/', save_data, name='save_data_url'),
    path('save-data-rule/', save_data_rule, name='save_data_url_rule'),
    path('transf/', transf, name='transf'),
    path('delete/', delete, name='delete'),
    path('edit_movimentacao/', views.edit_movimentacao, name='edit_movimentacao'),
    path('delete_movimentacao/<int:id>/', views.delete_movimentacao, name='delete_movimentacao'),
    path('get_movimentacao/<int:id>/', views.get_movimentacao, name='get_movimentacao'),

]
