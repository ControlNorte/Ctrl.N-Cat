from datetime import *
import pandas as pd
from django import forms, template
from .models import *
from django.db import connection
from .alteracoesdb import *
import ahocorasick
from django.db.models import Sum, Q
from django.http import HttpResponse

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

    # Verificar se há valores NaT
    if dados['Data'].isna().any():
        return print("Erro: Algumas datas não puderam ser convertidas. Verifique o formato das datas no arquivo Excel.")

    dados_dict = dados.to_dict('records')

    # Criar o autômato Aho-Corasick
    A = ahocorasick.Automaton()
    regras = Regra.objects.for_tenant(request.tenant).filter(cliente=cliente).select_related('categoria',
                                                                                             'subcategoria',
                                                                                             'centrodecusto')
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
        if MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente, banco=banco,
                                                                          data=dado['Data'], descricao=descricao,
                                                                          valor=dado['Valor']).exists():
            a = MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente, banco=banco,
                                                                               data=dado['Data'], descricao=descricao,
                                                                               valor=dado['Valor'])

            continue  # Pula para o próximo dado se já existir uma movimentação igual

        matched = False  # Indicador de correspondência

        # Itera pelas correspondências usando o autômato
        for _, (_, regra) in A.iter(descricao):
            movimentacoes_to_create.append(MovimentacoesCliente(
                tenant=request.tenant,
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
                tenant=request.tenant,
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
        datafinal = MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente,
                                                                                   banco=banco).order_by(
            '-data').first()
        datafinal = datafinal.data + timedelta(days=31) if datafinal else datetime.strptime(datainicial,
                                                                                            "%Y-%m-%d") + timedelta(
            days=31)  # Determina a maior data entre as movimentações

        tenant = int(request.tenant.id)
        cliente = cliente.id
        banco = banco.id

        while datainicial <= datafinal:
            # Calcula o saldo inicial e final do dia
            saldo_inicial = Saldo.objects.for_tenant(request.tenant).get(cliente=cliente, banco=banco,
                                                                         data=datainicial - timedelta(days=1))

            saldo_inicial = saldo_inicial.saldofinal if saldo_inicial else 0  # Obtém o saldo final do dia anterior

            saldo_movimentacoes = \
                MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente, banco=banco,
                                                                               data=datainicial).aggregate(
                    total_movimentacoes=Sum('valor'))['total_movimentacoes'] or 0

            saldo_final = saldo_inicial + saldo_movimentacoes

            with connection.cursor() as cursor:
                insert_query = """
                                    INSERT INTO financeiro_saldo (tenant_id, cliente_id, banco_id, data, saldoinicial, saldofinal)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (tenant_id, cliente_id, banco_id, data)
                                    DO UPDATE SET saldoinicial = EXCLUDED.saldoinicial, saldofinal = EXCLUDED.saldofinal;
                                """

                cursor.execute(insert_query, [
                    tenant,
                    cliente,
                    banco,
                    datainicial,
                    saldo_inicial,
                    saldo_final
                ])

            datainicial += timedelta(days=1)  # Incrementa o dia

    return print(f'Importação concluída. {conciliados} movimentações conciliadas.')  # Retorna uma mensagem de sucesso


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']


def pesquisa_db(tenant, cliente, id=None, dt_i=None, dt_f=None, descricao=None, detalhe=None, banco=None, centro_custo=None,
                categoria=None, sub_categoria=None, vl_i=None, vl_f=None, tipo=None):

    filtrados = MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente=cliente)

    # Aplica filtros apenas se os parâmetros não forem None
    if id is not None:
        filtrados = filtrados.filter(id=id)
    if descricao is not None:
        filtrados = filtrados.filter(descricao__icontains=descricao)
    if detalhe is not None:
        filtrados = filtrados.filter(detalhe__icontains=detalhe)
    if banco is not None:
        filtrados = filtrados.filter(banco=banco)
    if centro_custo is not None:
        filtrados = filtrados.filter(centrodecusto=centro_custo)
    if categoria is not None:
        filtrados = filtrados.filter(categoria=categoria)
    if sub_categoria is not None:
        filtrados = filtrados.filter(subcategoria=sub_categoria)
    if tipo is not None:
        if tipo == "entrada":
            filtrados = filtrados.filter(valor__gte=0)
        if tipo == "saida":
            filtrados = filtrados.filter(valor__lte=0)


    # Filtros de valores
    if vl_i is not None and vl_f is not None:
        # Se ambas as datas estão fornecidas, filtrar pelo intervalo
        filtrados = filtrados.filter(valor__range=[vl_i, vl_f])
    elif vl_i is not None:
        # Se apenas a data inicial for fornecida, filtrar a partir dela
        filtrados = filtrados.filter(valor__gte=vl_i)
    elif vl_f is not None:
        # Se apenas a data final for fornecida, filtrar até essa data
        filtrados = filtrados.filter(valor__lte=vl_f)

    # Filtros de datas
    if dt_i is not None and dt_f is not None:
        # Se ambas as datas estão fornecidas, filtrar pelo intervalo
        filtrados = filtrados.filter(data__range=[dt_i, dt_f])
    elif dt_i is not None:
        # Se apenas a data inicial for fornecida, filtrar a partir dela
        filtrados = filtrados.filter(data__gte=dt_i)
    elif dt_f is not None:
        # Se apenas a data final for fornecida, filtrar até essa data
        filtrados = filtrados.filter(data__lte=dt_f)

    return filtrados


def export_to_excel(request, tenant, cliente):
    # Captura os parâmetros GET
    id_param = request.GET.get('id')
    tipo_param = request.GET.get('tipo')
    dt_i_param = request.GET.get('dt_i')
    dt_f_param = request.GET.get('dt_f')
    descricao_param = request.GET.get('descricao')
    detalhe_param = request.GET.get('detalhe')
    banco_param = request.GET.get('banco')
    centro_custo_param = request.GET.get('centro_custo')
    categoria_param = request.GET.get('categoria')
    sub_categoria_param = request.GET.get('sub_categoria')
    valor_inicial_param = request.GET.get('vl_i')
    valor_final_param = request.GET.get('vl_f')

    # Inicia o queryset
    queryset = MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente=cliente)

    # Aplica os filtros, se houver
    if id_param:
        queryset = queryset.filter(id=id_param)
    if descricao_param:
        queryset = queryset.filter(descricao__icontains=descricao_param)
    if detalhe_param:
        queryset = queryset.filter(detalhe__icontains=detalhe_param)
    if banco_param:
        queryset = queryset.filter(banco=banco_param)
    if centro_custo_param:
        queryset = queryset.filter(centrodecusto=centro_custo_param)
    if categoria_param:
        queryset = queryset.filter(categoria=categoria_param)
    if sub_categoria_param:
        queryset = queryset.filter(subcategoria=sub_categoria_param)
    if tipo_param:
        if tipo_param == "entrada":
            queryset = queryset.filter(valor__gte=0)
        if tipo_param == "saida":
            queryset = queryset.filter(valor__lte=0)

    # Filtros de valores
    if valor_inicial_param and valor_final_param:
        # Se ambas as datas estão fornecidas, filtrar pelo intervalo
        queryset = queryset.filter(valor__range=[valor_inicial_param, valor_final_param])
    elif valor_inicial_param:
        # Se apenas a data inicial for fornecida, filtrar a partir dela
        queryset = queryset.filter(valor__gte=valor_inicial_param)
    elif valor_final_param:
        # Se apenas a data final for fornecida, filtrar até essa data
        queryset = queryset.filter(valor__lte=valor_final_param)

    # Filtros de datas
    if dt_i_param and dt_f_param:
        # Se ambas as datas estão fornecidas, filtrar pelo intervalo
        queryset = queryset.filter(data__range=[dt_i_param, dt_f_param])
    elif dt_i_param:
        # Se apenas a data inicial for fornecida, filtrar a partir dela
        queryset = queryset.filter(data__gte=dt_i_param)
    elif dt_f_param:
        # Se apenas a data final for fornecida, filtrar até essa data
        queryset = queryset.filter(data__lte=dt_f_param)

    # Converta o queryset em uma lista de dicionários
    data = list(queryset.values(
        'id', 'data', 'descricao', 'detalhe', 'banco__banco', 'centrodecusto__nome', 'categoria__nome', 'subcategoria__nome', 'valor'
    ))

    # Crie um DataFrame Pandas a partir da lista de dicionários
    df = pd.DataFrame(data)

    # Defina o tipo de resposta como 'application/vnd.ms-excel'
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="movimentacoes_cliente.xlsx"'

    # Escreva o DataFrame em um arquivo Excel
    df.to_excel(response, index=False, engine='openpyxl')

    return response
