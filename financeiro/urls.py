from dask.dataframe.io.demo import names
from django.urls import path, re_path
from . import views
from .views import *
from .api_pluggy import handle_item_data, recice_webhook
from .teste import download_modelo_importacao_cadastro_subcategoria, download_modelo_importacao_cadastro_centrodecusto

# from django.contrib.auth import views as auth_view

app_name = 'financeiro'

urlpatterns = [
    path('', financeiro_view, name='financeiro'),
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
    path('financeirocliente/maisopicoes/banco/editar/<int:id>', editarbanco, name='editarbanco'),
    path('financeirocliente/maisopicoes/banco/saldo/<int:id>', bancosaldo, name='bancosaldo'),

    path('financeirocliente/maisopicoes/categoria/', categoria, name='categoria'),
    path('financeirocliente/maisopicoes/categoria/editar/<int:id>', editarcategoria, name='editarcategoria'),

    path('financeirocliente/maisopicoes/subcategoria/', subcategoria, name='subcategoria'),
    path('financeirocliente/maisopicoes/subcategoria/editar/<int:id>', editarsubcategoria, name='editarsubcategoria'),

    path('financeirocliente/maisopicoes/centrocusto/', centrocusto, name='centrocusto'),
    path('financeirocliente/maisopicoes/centrocusto/editar/<int:id>', editarcentrocusto, name='editarcentrocusto'),

    path('financeirocliente/maisopicoes/regra/', regra, name='regra'),
    path('financeirocliente/maisopicoes/regra/editar/<int:id>', editarregra, name='editarregra'),

    path('save-data/', salvar_movimentacao, name='save_data_url'),
    path('save-data-rule/', salvar_regra_usando_movimentacao, name='save_data_url_rule'),
    path('transf/', transf, name='transf'),
    path('delete/', deletar_movimentacao, name='delete'),
    path('edit_movimentacao/', views.edit_movimentacao, name='edit_movimentacao'),
    path('delete_movimentacao/<int:id>/', views.delete_movimentacao, name='delete_movimentacao'),
    path('get_movimentacao/<int:id>/', views.get_movimentacao, name='get_movimentacao'),
    path('exportar-excel/<int:tenant>/<int:cliente>', views.export_to_excel, name='export_to_excel'),

    path('api/item-data/', handle_item_data, name='handle_item_data'),
    path('recive-webhook/', recice_webhook, name='recive_webhook'),

    path('download_modelo_importacao_sb/', download_modelo_importacao_cadastro_subcategoria, name='download_modelo_importacao_cadastro_subcategoria'),
    path('download_modelo_importacao_cc/', download_modelo_importacao_cadastro_centrodecusto, name='download_modelo_importacao_cadastro_centrodecusto'),
]
