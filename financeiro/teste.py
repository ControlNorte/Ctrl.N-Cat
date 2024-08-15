from datetime import *
import pandas as pd
from django import forms, template
from .models import UploadedFile
from jinja2 import Template, Environment, FileSystemLoader
from .models import *
from django.middleware.csrf import get_token
from .alteracoesdb import *
import ahocorasick
import os

register = template.Library()

def mes(num):
    meses = {
        1: 'Jan',
        2: 'Fev',
        3: 'Mar',
        4: 'Abr',
        5: 'Mai',
        6: 'Jun',
        7: 'Jul',
        8: 'Ago',
        9: 'Set',
        10: 'Out',
        11: 'Nov',
        12: 'Dez',
    }
    mees = meses.get(num)
    return mees


def messtr(messtring):
    meses = {
        'Jan': 1,
        'Fev': 2,
        'Mar': 3,
        'Abr': 4,
        'Mai': 5,
        'Jun': 6,
        'Jul': 7,
        'Ago': 8,
        'Set': 9,
        'Out': 10,
        'Nov': 11,
        'Dez': 12,
    }
    meesstr = meses.get(messtring)
    return meesstr


def manter_no_original(row):
    if 'saldo' in row['descricao'].lower():
        return row['valor']
    else:
        return ''


# Função para formatar a data
def format_date(value):
    return value.strftime('%d/%m/%Y')


# Função para formatar o valor
def format_currency(value):
    return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def importar_arquivo_excel(arquivo_upload, cliente, banco, request):
    try:
        # Verificar se o arquivo foi fornecido
        if not arquivo_upload:
            return "Erro: Nenhum arquivo foi selecionado."

        # Carregar os dados do Excel
        dados = pd.read_excel(arquivo_upload, dtype={'Descrição': str, 'Data': str, 'Valor': float})

        # Converter as datas levando em consideração diferentes formatos
        dados['Data'] = pd.to_datetime(dados['Data'])

        # Verificar se há valores NaT (resultantes de erros na conversão de datas)
        if dados['Data'].isna().any():
            print('erro')
            return "Erro: Algumas datas não puderam ser convertidas. Verifique o formato das datas no arquivo Excel."

        dados = dados.to_dict('records')

        # Criar o autômato Aho-Corasick
        A = ahocorasick.Automaton()
        regras = Regra.objects.filter(cliente=cliente).select_related('categoria', 'subcategoria', 'centrodecusto')
        for idx, regra in enumerate(regras):
            A.add_word(str(regra.descricao), (idx, regra))
        A.make_automaton()

        movimentacoes_to_create = []
        transicoes_to_create = []
        conciliados = 0
        i = 0

        while i < len(dados):
            descricao = dados[i]['Descrição']
            linha_removida = False

            for end_index, (idx, regra) in A.iter(descricao):
                movimentacoes_to_create.append(MovimentacoesCliente(
                    cliente=cliente,
                    banco=banco,
                    data=dados[i]['Data'].date(),
                    descricao=descricao,
                    detalhe='Sem Detalhe',
                    valor=dados[i]['Valor'],
                    categoria=regra.categoria,
                    subcategoria=regra.subcategoria,
                    centrodecusto=regra.centrodecusto
                ))
                del dados[i]
                linha_removida = True
                conciliados += 1
                break

            if not linha_removida:
                transicoes_to_create.append(TransicaoCliente(
                    cliente=cliente,
                    banco=banco,
                    data=dados[i]['Data'].date(),
                    descricao=dados[i]['Descrição'],
                    valor=dados[i]['Valor']
                ))
                i += 1

        # Salvar movimentações e transições em batch
        if movimentacoes_to_create:
            MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)

        if transicoes_to_create:
            TransicaoCliente.objects.bulk_create(transicoes_to_create)

        # Atualizar saldo baseado nas novas movimentações

        for movimentacao in movimentacoes_to_create:
            alteracaosaldo(banco=banco.id, cliente=cliente, data=str(movimentacao.data))
            print(f'Saldo atualizado para {movimentacao.data}')

        return f'Importação concluída. {conciliados} movimentações conciliadas.'

    except Exception as e:
        print(f"Erro ao importar arquivo: {e}")
        return f"Erro ao importar arquivo: {e}"


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']
