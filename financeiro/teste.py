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
from sqlalchemy import create_engine

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
        if not arquivo_upload:
            return "Erro: Nenhum arquivo foi selecionado."

        # Carregar e processar os dados do Excel
        dados = pd.read_excel(arquivo_upload, dtype={'Descrição': str, 'Data': str, 'Valor': float})
        dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')

        # Verificar se há valores NaT
        if dados['Data'].isna().any():
            return "Erro: Algumas datas não puderam ser convertidas. Verifique o formato das datas no arquivo Excel."

        dados_dict = dados.to_dict('records')

        # Criar o autômato Aho-Corasick
        A = ahocorasick.Automaton()
        regras = Regra.objects.filter(cliente=cliente).select_related('categoria', 'subcategoria', 'centrodecusto')
        for idx, regra in enumerate(regras):
            A.add_word(str(regra.descricao), (idx, regra))
        A.make_automaton()

        movimentacoes_to_create = []
        transicoes_to_create = []
        conciliados = 0

        # Processamento das transações
        for dado in dados_dict:
            descricao = dado['Descrição']
            matched = False

            for _, (_, regra) in A.iter(descricao):
                movimentacoes_to_create.append(MovimentacoesCliente(
                    cliente=cliente,
                    banco=banco,
                    data=dado['Data'].date(),
                    descricao=descricao,
                    detalhe='Sem Detalhe',
                    valor=dado['Valor'],
                    categoria=regra.categoria,
                    subcategoria=regra.subcategoria,
                    centrodecusto=regra.centrodecusto
                ))
                matched = True
                conciliados += 1
                break

            if not matched:
                transicoes_to_create.append(TransicaoCliente(
                    cliente=cliente,
                    banco=banco,
                    data=dado['Data'].date(),
                    descricao=descricao,
                    valor=dado['Valor']
                ))

        # Inserção em batch das movimentações e transições
        if movimentacoes_to_create:
            MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)

        if transicoes_to_create:
            TransicaoCliente.objects.bulk_create(transicoes_to_create)

        # Atualização do saldo baseado nas novas movimentações
        if movimentacoes_to_create:
            datainicial = min(mov.data for mov in movimentacoes_to_create)
            datafinal = max(mov.data for mov in movimentacoes_to_create)

            db_url = r"postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
            engine = create_engine(db_url)

            with engine.connect() as conexao:
                query_saldo = f"""
                SELECT * FROM financeiro_saldo 
                WHERE cliente_id = {cliente.id} 
                AND banco_id = {int(banco)} 
                AND data BETWEEN '{datainicial}' AND '{datafinal}'
                """
                tabela_saldo = pd.read_sql(query_saldo, conexao)

                query_movimentacoes = f"""
                SELECT * FROM financeiro_movimentacoescliente 
                WHERE cliente_id = {cliente.id} 
                AND banco_id = {int(banco)} 
                AND data BETWEEN '{datainicial}' AND '{datafinal}'
                """
                tabela_movimentacoes = pd.read_sql(query_movimentacoes, conexao)

                saldo_atualizacoes = []
                current_date = datainicial

                while current_date <= datafinal:
                    data_str = current_date.strftime('%Y-%m-%d')
                    data_anterior_str = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')

                    saldoinicial = tabela_saldo.loc[tabela_saldo['data'] == data_anterior_str, 'saldofinal'].sum() or 0
                    saldodia = tabela_movimentacoes.loc[tabela_movimentacoes['data'] == data_str, 'valor'].sum() or 0
                    saldofinal = saldoinicial + saldodia

                    saldo_atualizacoes.append(Saldo(
                        data=data_str,
                        banco=BancosCliente.objects.get(id=banco),
                        cliente=cliente,
                        saldoinicial=float(saldoinicial),
                        saldofinal=float(saldofinal)
                    ))

                    current_date += timedelta(days=1)

                Saldo.objects.bulk_update(saldo_atualizacoes, ['saldoinicial', 'saldofinal'])

        return f'Importação concluída. {conciliados} movimentações conciliadas.'

    except Exception as e:
        logger.error(f"Erro ao importar arquivo: {e}")
        return f"Erro ao importar arquivo: {e}"
        


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']
