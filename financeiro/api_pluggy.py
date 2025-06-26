import datetime
import time as tm
from datetime import *
from time import process_time_ns
from urllib.parse import urlencode, urlparse, parse_qs

import ahocorasick
import json
import re
import requests
import threading

from dateutil.utils import today
from django.db import connection
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from decimal import Decimal
from django.utils.dateparse import parse_date

from hpinicial.models import Tenant
from .models import BancosCliente, cadastro_de_cliente, Regra, MovimentacoesCliente, TransicaoCliente, Saldo

@csrf_exempt # Use apenas para testes; idealmente, configure o CSRF corretamente.
def handle_item_data(request):

    # Converte o corpo da requisição JSON em dicionário Python
    data = json.loads(request.body)
    body = json.loads(request.body.decode("utf-8"))  # Converte o corpo da requisição para um dicionário
    accessToken = body.get("accessToken")  # Obtém o token do JSON

    itemId = data['itemData']['item']['id']

    banco = data['itemData']['item']['connector']['name']


    payload = {
        "clientId": "8e0a0ef7-71f4-4049-ac54-bab15e6c7bb9",
        "clientSecret": "6ec284c2-cc80-4718-a2d2-5efc1aeb6d52"}

    url = "https://api.pluggy.ai/auth"

    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    api_key = response.text
    api_key = json.loads(api_key)
    api_key = api_key['apiKey']

    if request.method == 'POST':
        # try:
        # Lista de contas
        url = f"https://api.pluggy.ai/accounts"

        params = {"itemId": itemId,
                  "type": "BANK"}

        query_string = urlencode(params)
        url = f"{url}?{query_string}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": api_key
        }

        response = requests.get(url, headers=headers)

        dados_banco = response.json()

        transferNumber = dados_banco['results'][0]['bankData']['transferNumber']

        separated_parts = re.split(r'[/-]', transferNumber)

        # Atribuir às variáveis
        agencia = separated_parts[0]
        conta = separated_parts[1]
        digito = separated_parts[2]

        # Criando banco no banco de dados
        pk = request.session.get('dadoscliente')

        if not pk:
            print("sem pk")
        dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)

        bancos = BancosCliente.objects.filter(transferNumber=transferNumber)

        if not bancos.exists():
            banco = BancosCliente.objects.create(
                tenant=request.tenant,
                cliente=dadoscliente,
                banco=banco,
                agencia=agencia,
                conta=conta,
                digito=digito,
                ativo=True,
                transferNumber=transferNumber,
                isConnected = True,
            )
            banco.save()
            print("Banco cadastrado com sucesso!")

        else:
            print("Banco já cadastrado!")

        accountId = dados_banco['results'][0]['id']

        bancos = BancosCliente.objects.get(transferNumber=transferNumber)

        cliente = bancos.cliente
        tenant = bancos.tenant

        url = "https://api.pluggy.ai/transactions"

        to_date = date.today()

        from_date = to_date - timedelta(days=31)

        params = {"accountId": accountId,
                  "from": from_date,
                  "to": to_date,
                  "pageSize": 500,
                  }

        query_string = urlencode(params)
        url = f"{url}?{query_string}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": api_key
        }

        response = requests.get(url, headers=headers)
        results_json = response.json()

        # Inicializa com os dados da primeira página
        all_transactions = results_json.get('results', [])
        totalPages = results_json.get('totalPages', 1)
        paginaAtual = 2  # Começa da 2ª página

        # Loop para buscar as próximas páginas
        while paginaAtual <= totalPages:
            params.update({"page": paginaAtual})
            query_string = urlencode(params)
            paged_url = f"{url}?{query_string}"

            response = requests.get(paged_url, headers=headers)
            page_data = response.json()

            transactions = page_data.get('results', [])
            all_transactions.extend(transactions)

            paginaAtual += 1

        results = all_transactions

        dados = []

        tenant = Tenant.objects.get(nome=tenant)
        tenant = tenant.id
        cliente = cadastro_de_cliente.objects.get(razao_social=cliente)
        cliente = cliente.id
        banco = bancos.id

        for result in results:
            if result['status'] == 'POSTED':
                descricao = result['description']
                valor = result['amount']
                data = result['date']
                data = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')

                registro = {
                    'data': data,
                    'descricao': descricao,
                    'valor': valor
                }

                dados.append(registro)

        movimentacoes_to_create = []  # Lista para armazenar as movimentações que serão criadas
        transicoes_to_create = []  # Lista para armazenar as transições que serão criadas
        conciliados = 0  # Contador para o número de movimentações conciliadas

        # Criar o autômato Aho-Corasick
        A = ahocorasick.Automaton()
        regras = Regra.objects.for_tenant(tenant).filter(cliente_id=cliente).select_related('categoria',
                                                                                                 'subcategoria',
                                                                                                 'centrodecusto')
        if not regras.exists():

            for dado in dados:
                descricao_normalizada = descricao.strip().lower()
                valor_normalizado = Decimal(str(dado['valor'])).quantize(Decimal('0.01'))
                data_normalizada = parse_date(str(dado['data']))

                if (
                    MovimentacoesCliente.objects.for_tenant(tenant)
                    .filter(
                        cliente_id=cliente,
                        banco_id=banco,
                        data=data_normalizada,
                        descricao__iexact=descricao_normalizada,
                        valor=valor_normalizado,
                    )
                    .exists()
                    or
                    TransicaoCliente.objects
                    .filter(
                        cliente_id=cliente,
                        banco_id=banco,
                        data=data_normalizada,
                        descricao__iexact=descricao_normalizada,
                        valor=valor_normalizado,
                    )
                    .exists()
                ):
                    print(f'Movimentação já conciliada: data: {dado["data"]}, descrição: {descricao}, valor: {dado["valor"]}')


                    continue

                descricao = dado['descricao'].upper()
                descricao = descricao[:100]
                matched = False

                if not matched:  # Se nenhuma correspondência foi encontrada
                    transicoes_to_create.append(TransicaoCliente(
                        tenant_id=tenant,
                        cliente_id=cliente,
                        banco_id=banco,
                        data=dado['data'],
                        descricao=descricao,
                        valor=dado['valor']
                    ))
                    conciliados += 1
        else:

            for idx, regra in enumerate(regras):
                A.add_word(str(regra.descricao).upper(), (idx, regra))
            A.make_automaton() # Compila o autômato para otimizar a pesquisa

            # Processamento das transações
            for dado in dados:

                descricao_raw = dado['descricao']
                descricao_upper = descricao_raw.upper()[:100]
                descricao_normalizada = descricao_raw.strip().lower()
                valor_normalizado = Decimal(str(dado['valor'])).quantize(Decimal('0.01'))
                data_normalizada = parse_date(str(dado['data']))

                if (
                        MovimentacoesCliente.objects.for_tenant(tenant)
                                .filter(
                            cliente_id=cliente,
                            banco_id=banco,
                            data=data_normalizada,
                            descricao__iexact=descricao_normalizada,
                            valor=valor_normalizado,
                        )
                                .exists()
                        or
                        TransicaoCliente.objects
                                .filter(
                            cliente_id=cliente,
                            banco_id=banco,
                            data=data_normalizada,
                            descricao__iexact=descricao_normalizada,
                            valor=valor_normalizado,
                        )
                                .exists()
                ):
                    print(
                        f'Movimentação já conciliada: data: {dado["data"]}, descrição: {descricao}, valor: {dado["valor"]}')

                    continue

                matched = False  # Indicador de correspondência

                # Itera pelas correspondências usando o autômato
                for _, (_, regra) in A.iter(descricao):
                    movimentacoes_to_create.append(MovimentacoesCliente(
                        tenant_id=tenant,
                        cliente_id=cliente,
                        banco_id=banco,
                        data=data_normalizada,
                        descricao=descricao_upper,
                        detalhe='Sem Detalhe',
                        valor=valor_normalizado,
                        categoria=regra.categoria,
                        subcategoria=regra.subcategoria,
                        centrodecusto=regra.centrodecusto
                    ))
                    matched = True  # Marca como correspondido

                    break  # Sai do loop após a primeira correspondência

                if not matched:  # Se nenhuma correspondência foi encontrada
                    transicoes_to_create.append(TransicaoCliente(
                        tenant_id=tenant,
                        cliente_id=cliente,
                        banco_id=banco,
                        data=data_normalizada,
                        descricao=descricao_upper,
                        valor=valor_normalizado
                    ))
                    conciliados += 1  # Incrementa o contador de movimentações conciliadas

        # Inserção em batch das movimentações no banco de dados
        if movimentacoes_to_create:
            MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)

        # Inserção em batch das transições no banco de dados
        if transicoes_to_create:
            TransicaoCliente.objects.bulk_create(transicoes_to_create)

        # Atualização do saldo baseado nas novas movimentações
        if movimentacoes_to_create:
            datainicial = min(
                mov.data if isinstance(mov.data, date) else datetime.strptime(mov.data, "%Y-%m-%d").date()
                for mov in movimentacoes_to_create
            )

            datafinal = MovimentacoesCliente.objects.for_tenant(tenant).filter(
                cliente_id=cliente, banco_id=banco).order_by('-data').first()

            datafinal = datafinal.data + timedelta(days=31) if datafinal else datetime.strptime(
                datainicial,"%Y-%m-%d") + timedelta(days=31)  # Determina a maior data entre as movimentações

            while datainicial <= datafinal:
                # Calcula o saldo inicial e final do dia
                saldo_inicial = Saldo.objects.for_tenant(tenant).get(
                    cliente_id=cliente, banco_id=banco,data=datainicial - timedelta(days=1))

                saldo_inicial = saldo_inicial.saldofinal if saldo_inicial else 0  # Obtém o saldo final do dia anterior

                saldo_movimentacoes = \
                    MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente_id=cliente, banco_id=banco,
                                                                                   data=datainicial).aggregate(
                        total_movimentacoes=Sum('valor'))['total_movimentacoes'] or 0

                saldo_final = saldo_inicial + saldo_movimentacoes



                with connection.cursor() as cursor:
                    insert_query = """
                                        INSERT INTO financeiro_saldo (tenant_id, cliente_id, banco_id, data, saldoinicial, saldofinal)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                        ON CONFLICT(cliente_id, banco_id, data)
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


        print(f'Banco cadastrado com seucesso! Importamos {conciliados} movimentações para te ajudar!.') # Retorna uma mensagem de sucesso
        return JsonResponse({'message': f'Banco cadastrado com seucesso! Importamos {conciliados} movimentações para te ajudar!'}, status=200)

    # except Exception as e:
    #     print("Erro")
    #     return JsonResponse({'error': str(e)}, status=400)

        # Enviar mensagem via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "notificacoes",  # Grupo de WebSockets que criamos
            {
                "type": "send_notification",
                "message": f"Banco cadastrado! {conciliados} movimentações importadas."
            }
        )

    return JsonResponse({'error': 'Método não permitido'}, status=405)



@csrf_exempt
def recice_webhook(request):
    webhook = request.body

    if not webhook:
        webhook = "Sem transações a serem lançadas"

    # print(webhook)
    threading.Thread(target=process_webhook, args=(webhook,)).start()
    return JsonResponse({'status': 'success', 'message': 'Webhook received successfully'}, status=200)


def process_webhook(webhook):
    if webhook == "Sem transações a serem lançadas":
        return print(webhook)

    webhook = json.loads(webhook)
    event = webhook['event']

    payload = {
        "clientId": "8e0a0ef7-71f4-4049-ac54-bab15e6c7bb9",
        "clientSecret": "6ec284c2-cc80-4718-a2d2-5efc1aeb6d52"}


    if event == 'transactions/created':

        # Criando acess_token
        url = "https://api.pluggy.ai/auth"

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        api_key = response.text
        api_key = json.loads(api_key)
        api_key = api_key['apiKey']

        # Requisitando dados da conta
        accountId = webhook['accountId']

        url = f"https://api.pluggy.ai/accounts/{accountId}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": api_key
        }

        response = requests.get(url, headers=headers)

        dados_banco = response.json()

        if dados_banco['type'] == "BANK":
            transferNumber = dados_banco['bankData']['transferNumber']
        else:
            return print(dados_banco['type'])

        timeout = 10
        start_time = tm.time()
        bancos = None

        while tm.time() - start_time < timeout:
            try:
                bancos = BancosCliente.objects.get(transferNumber=transferNumber)
                break
            except BancosCliente.DoesNotExist:
                tm.sleep(1)  # espera 1 segundo e tenta de novo

        if not bancos:
            raise Exception("BancosCliente com transferNumber não encontrado após 10 segundos")

        bancos = BancosCliente.objects.get(transferNumber=transferNumber)
        cliente = bancos.cliente
        tenant = bancos.tenant

        url = "https://api.pluggy.ai/transactions"
        params = {"accountId": accountId,
                  "pageSize": 500,
                  "createdAtFrom": webhook["transactionsCreatedAtFrom"],
                  }

        query_string = urlencode(params)
        url = f"{url}?{query_string}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": api_key
        }


        response = requests.get(url, headers=headers)
        results_json = response.json()
        # Inicializa com os dados da primeira página
        all_transactions = results_json.get('results', [])
        totalPages = results_json.get('totalPages', 1)
        paginaAtual = 2  # Começa da 2ª página

        # Loop para buscar as próximas páginas
        while paginaAtual <= totalPages:
            params.update({"page": paginaAtual})
            query_string = urlencode(params)
            paged_url = f"{url}?{query_string}"

            response = requests.get(paged_url, headers=headers)

            page_data = response.json()

            transactions = page_data.get('results', [])
            all_transactions.extend(transactions)

            paginaAtual += 1

        results = all_transactions
        dados = []

        tenant = Tenant.objects.get(nome=tenant)
        tenant = tenant.id
        cliente = cadastro_de_cliente.objects.get(razao_social=cliente)
        cliente = cliente.id
        banco = bancos.id

        for result in results:
            data = result['date']
            data = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S.%fZ')  # mantém como datetime
            if result['status'] == 'POSTED' and data >= datetime.now() - timedelta(days=30):
                descricao = result['description']
                valor = result['amount']

                registro = {
                    'data': data,
                    'descricao': descricao,
                    'valor': valor
                }

                dados.append(registro)
            else:
                continue

        movimentacoes_to_create = []  # Lista para armazenar as movimentações que serão criadas
        transicoes_to_create = []  # Lista para armazenar as transições que serão criadas
        conciliados = 0  # Contador para o número de movimentações conciliadas

        # Criar o autômato Aho-Corasick
        A = ahocorasick.Automaton()
        regras = Regra.objects.for_tenant(tenant).filter(cliente_id=cliente).select_related('categoria',
                                                                                            'subcategoria',
                                                                                            'centrodecusto')
        if not regras.exists():

            for dado in dados:
                descricao_normalizada = descricao.strip().lower()
                valor_normalizado = Decimal(str(dado['valor'])).quantize(Decimal('0.01'))
                data_normalizada = parse_date(str(dado['data']))

                if (
                        MovimentacoesCliente.objects.for_tenant(tenant)
                                .filter(
                            cliente_id=cliente,
                            banco_id=banco,
                            data=data_normalizada,
                            descricao__iexact=descricao_normalizada,
                            valor=valor_normalizado,
                        )
                                .exists()
                        or
                        TransicaoCliente.objects
                                .filter(
                            cliente_id=cliente,
                            banco_id=banco,
                            data=data_normalizada,
                            descricao__iexact=descricao_normalizada,
                            valor=valor_normalizado,
                        )
                                .exists()
                ):
                    print(
                        f'Movimentação já conciliada: data: {dado["data"]}, descrição: {descricao}, valor: {dado["valor"]}')

                    continue

                descricao = dado['descricao'].upper()
                descricao = descricao[:100]
                matched = False

                if not matched:  # Se nenhuma correspondência foi encontrada
                    transicoes_to_create.append(TransicaoCliente(
                        tenant_id=tenant,
                        cliente_id=cliente,
                        banco_id=banco,
                        data=dado['data'],
                        descricao=descricao,
                        valor=dado['valor']
                    ))
                    conciliados += 1
        else:

            for idx, regra in enumerate(regras):
                A.add_word(str(regra.descricao).upper(), (idx, regra))
            A.make_automaton()  # Compila o autômato para otimizar a pesquisa

            # Processamento das transações
            for dado in dados:
                descricao = dado['descricao'].upper()
                descricao = descricao[:100]

                descricao_normalizada = descricao.strip().lower()
                valor_normalizado = Decimal(str(dado['valor'])).quantize(Decimal('0.01'))
                data_normalizada = parse_date(str(dado['data']))

                if (
                        MovimentacoesCliente.objects.for_tenant(tenant)
                                .filter(
                            cliente_id=cliente,
                            banco_id=banco,
                            data=data_normalizada,
                            descricao__iexact=descricao_normalizada,
                            valor=valor_normalizado,
                        )
                                .exists()
                        or
                        TransicaoCliente.objects
                                .filter(
                            cliente_id=cliente,
                            banco_id=banco,
                            data=data_normalizada,
                            descricao__iexact=descricao_normalizada,
                            valor=valor_normalizado,
                        )
                                .exists()
                ):
                    print(
                        f'Movimentação já conciliada: data: {dado["data"]}, descrição: {descricao}, valor: {dado["valor"]}')

                    continue

                matched = False  # Indicador de correspondência

                # Itera pelas correspondências usando o autômato
                for _, (_, regra) in A.iter(descricao):
                    movimentacoes_to_create.append(MovimentacoesCliente(
                        tenant_id=tenant,
                        cliente_id=cliente,
                        banco_id=banco,
                        data=dado['data'],
                        descricao=descricao,
                        detalhe='Sem Detalhe',
                        valor=dado['valor'],
                        categoria=regra.categoria,
                        subcategoria=regra.subcategoria,
                        centrodecusto=regra.centrodecusto
                    ))
                    matched = True  # Marca como correspondido

                    break  # Sai do loop após a primeira correspondência

                if not matched:  # Se nenhuma correspondência foi encontrada
                    transicoes_to_create.append(TransicaoCliente(
                        tenant_id=tenant,
                        cliente_id=cliente,
                        banco_id=banco,
                        data=dado['data'],
                        descricao=descricao,
                        valor=dado['valor']
                    ))
                    conciliados += 1  # Incrementa o contador de movimentações conciliadas

        # Inserção em batch das movimentações no banco de dados
        if movimentacoes_to_create:
            MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)

        # Inserção em batch das transições no banco de dados
        if transicoes_to_create:
            TransicaoCliente.objects.bulk_create(transicoes_to_create)

        # Atualização do saldo baseado nas novas movimentações
        if movimentacoes_to_create:
            datainicial = min(
                mov.data if isinstance(mov.data, date) else datetime.strptime(mov.data, "%Y-%m-%d").date()
                for mov in movimentacoes_to_create
            )

            datafinal = MovimentacoesCliente.objects.for_tenant(tenant).filter(
                cliente_id=cliente, banco_id=banco).order_by('-data').first()

            datafinal = datafinal.data + timedelta(days=31) if datafinal else datetime.strptime(
                datainicial, "%Y-%m-%d") + timedelta(days=31)  # Determina a maior data entre as movimentações

            while datainicial <= datafinal:
                # Calcula o saldo inicial e final do dia
                saldo_inicial = Saldo.objects.for_tenant(tenant).get(
                    cliente_id=cliente, banco_id=banco, data=datainicial - timedelta(days=1))

                saldo_inicial = saldo_inicial.saldofinal if saldo_inicial else 0  # Obtém o saldo final do dia anterior

                saldo_movimentacoes = \
                    MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente_id=cliente, banco_id=banco,
                                                                           data=datainicial).aggregate(
                        total_movimentacoes=Sum('valor'))['total_movimentacoes'] or 0

                saldo_final = saldo_inicial + saldo_movimentacoes

                with connection.cursor() as cursor:
                    insert_query = """
                                                INSERT INTO financeiro_saldo (tenant_id, cliente_id, banco_id, data, saldoinicial, saldofinal)
                                                VALUES (%s, %s, %s, %s, %s, %s)
                                                ON CONFLICT(cliente_id, banco_id, data)
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

        print(f'Importação concluída. {conciliados} movimentações conciliadas.')  # Retorna uma mensagem de sucesso
        return JsonResponse(
            data={'message': f'Importação concluída. {conciliados} movimentações conciliadas '},
            status=200)