from datetime import *
import pandas as pd
from django import forms, template
from .models import UploadedFile
from .models import *
from django.db import connection
from .alteracoesdb import *
import ahocorasick
from django.db.models import Sum, Q


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
    if not arquivo_upload:
        return print("Erro: Nenhum arquivo foi selecionado.")  # Retorna erro se nenhum arquivo foi selecionado

    # Carregar e processar os dados do Excel
    dados = pd.read_excel(arquivo_upload, dtype={'Descrição': str, 'Data': str, 'Valor': float})
    dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')  # Converte as datas para o formato datetime

    print(len(dados))

    # Verificar se há valores NaT
    if dados['Data'].isna().any():
        return print("Erro: Algumas datas não puderam ser convertidas. Verifique o formato das datas no arquivo Excel.")

    dados_dict = dados.to_dict('records')

    # Criar o autômato Aho-Corasick
    A = ahocorasick.Automaton()
    regras = Regra.objects.filter(cliente=cliente).select_related('categoria', 'subcategoria', 'centrodecusto')
    for idx, regra in enumerate(regras):
        A.add_word(str(regra.descricao).upper(), (idx, regra))  # Adiciona as descrições das regras no autômato
    A.make_automaton()  # Compila o autômato para otimizar a pesquisa

    movimentacoes_to_create = []  # Lista para armazenar as movimentações que serão criadas
    transicoes_to_create = []  # Lista para armazenar as transições que serão criadas
    conciliados = 0  # Contador para o número de movimentações conciliadas

    # Processamento das transações
    for dado in dados_dict:
        descricao = dado['Descrição'].upper()

        # Verifica se já existe uma movimentação com a mesma data, descrição e valor
        if MovimentacoesCliente.objects.filter(cliente=cliente, banco=banco, data=dado['Data'], descricao=descricao,
                                               valor=dado['Valor']).exists():
            continue  # Pula para o próximo dado se já existir uma movimentação igual

        matched = False  # Indicador de correspondência

        # Itera pelas correspondências usando o autômato
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
            matched = True  # Marca como correspondido
            conciliados += 1  # Incrementa o contador de movimentações conciliadas
            break  # Sai do loop após a primeira correspondência

        if not matched:  # Se nenhuma correspondência foi encontrada
            transicoes_to_create.append(TransicaoCliente(
                cliente=cliente,
                banco=banco,
                data=dado['Data'].date(),
                descricao=descricao,
                valor=dado['Valor']
            ))

    # Inserção em batch das movimentações no banco de dados
    if movimentacoes_to_create:
        MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)

    # Inserção em batch das transições no banco de dados
    if transicoes_to_create:
        TransicaoCliente.objects.bulk_create(transicoes_to_create)

    # Atualização do saldo baseado nas novas movimentações
    if movimentacoes_to_create:
        datainicial = min(mov.data for mov in movimentacoes_to_create)  # Determina a menor data entre as movimentações
        datafinal = MovimentacoesCliente.objects.filter(cliente=cliente, banco=banco).order_by('-data').first()
        datafinal = datafinal.data + timedelta(days=31) if datafinal else datetime.strptime(datainicial, "%Y-%m-%d") + timedelta(days=31)  # Determina a maior data entre as movimentações

        while datainicial <= datafinal:
            # Calcula o saldo inicial e final do dia
            saldo_inicial = Saldo.objects.get(cliente=cliente, banco=banco,
                                                 data=datainicial - timedelta(days=1))

            saldo_inicial = saldo_inicial.saldofinal if saldo_inicial else 0  # Obtém o saldo final do dia anterior

            saldo_movimentacoes = \
                MovimentacoesCliente.objects.filter(cliente=cliente, banco=banco, data=datainicial).aggregate(
                    total_movimentacoes=Sum('valor'))['total_movimentacoes'] or 0

            saldo_final = saldo_inicial + saldo_movimentacoes

            print(f'SI: {saldo_inicial}, SF: {saldo_final}, data: {datainicial}')

            with connection.cursor() as cursor:
                insert_query = """
                    INSERT INTO financeiro_saldo (cliente_id, banco_id, data, saldoinicial, saldofinal)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (cliente_id, banco_id, data)
                    DO UPDATE SET saldoinicial = EXCLUDED.saldoinicial, saldofinal = EXCLUDED.saldofinal;
                """

                cursor.execute(insert_query, [
                    cliente.id,
                    banco.id,
                    datainicial,
                    saldo_inicial,
                    saldo_final
                ])

            datainicial += timedelta(days=1)  # Incrementa o dia

    return print(f'Importação concluída. {conciliados} movimentações conciliadas.')  # Retorna uma mensagem de sucesso

MovimentacoesCliente
class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']
