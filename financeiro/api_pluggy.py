import datetime

import requests, json, re, threading, ahocorasick
from hpinicial.models import Tenant
from .models import BancosCliente, cadastro_de_cliente, Regra, MovimentacoesCliente, TransicaoCliente, Saldo
from dask.array import empty
from datetime import *
from django.db import connection
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlencode


@csrf_exempt  # Use apenas para testes; idealmente, configure o CSRF corretamente.
def handle_item_data(request):
    # Converte o corpo da requisição JSON em dicionário Python
    data = json.loads(request.body)

    itemId = data['item']['id']
    banco = data['item']['connector']['name']

    url = "https://api.pluggy.ai/auth"

    payload = {
        "clientId": "226a2d88-095c-4469-9943-1a3e6e3ae477",
        "clientSecret": "58b103c9-2272-4f7d-a1ef-80dd015704dc"
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    api_key = response.text

    payload = {
        "clientId": "226a2d88-095c-4469-9943-1a3e6e3ae477",
        "clientSecret": "58b103c9-2272-4f7d-a1ef-80dd015704dc"
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": api_key
    }

    response = requests.post(url, json=payload, headers=headers)

    access_token = response.text
    access_token = json.loads(access_token)

    if request.method == 'POST':
        try:
            # Lista de contas
            url = f"https://api.pluggy.ai/accounts"

            params = {"itemId": itemId,
                      "type": "BANK"}

            query_string = urlencode(params)
            url = f"{url}?{query_string}"

            headers = {
                "accept": "application/json",
                "X-API-KEY": access_token['apiKey']
            }

            response = requests.get(url, headers=headers)

            dados_banco = response.json()

            dados_banco = dados_banco['results'][0]['bankData']['transferNumber']
            transferNumber = dados_banco

            # Pegar o primeiro número
            first_number = dados_banco

            if '/' in dados_banco:
                # Separar usando regex
                separated_parts = re.split(r'[/-]', first_number)

                # Atribuir às variáveis
                agencia = separated_parts[1]
                conta = separated_parts[2]
                digito = separated_parts[3]

            else:
                agencia = 0
                conta = dados_banco
                digito = 0

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

            # Requisitando nome da conta
            url = f"https://api.pluggy.ai/items/{itemId}"

            headers = {
                "accept": "application/json",
                "X-API-KEY": access_token['apiKey']
            }

            response = requests.get(url, headers=headers)

            banco = response.json()
            banco = str(banco['connector']['name'])

            # Requisitando dados da conta
            url = f"https://api.pluggy.ai/accounts"

            params = {"itemId": itemId,
                      "type": "BANK"}

            query_string = urlencode(params)
            url = f"{url}?{query_string}"

            headers = {
                "accept": "application/json",
                "X-API-KEY": access_token['apiKey']
            }

            response = requests.get(url, headers=headers)

            dados_banco = response.json()

            transferNumber = dados_banco['results'][0]['bankData']['transferNumber']
            accountId = dados_banco['results'][0]['id']

            bancos = BancosCliente.objects.get(transferNumber=transferNumber)

            cliente = bancos.cliente
            tenant = bancos.tenant
            print(cliente)
            print(tenant)

            url = "https://api.pluggy.ai/transactions"

            to_date = date.today()
            from_date = to_date - timedelta(days=30)

            params = {"accountId": accountId,
                      "from": from_date,
                      "to": to_date,
                      }

            query_string = urlencode(params)
            url = f"{url}?{query_string}"

            headers = {
                "accept": "application/json",
                "X-API-KEY": access_token['apiKey']
            }

            response = requests.get(url, headers=headers)

            results = (response.json())
            print(results)
            results = results['results']

            dados = []

            tenant = Tenant.objects.get(nome=tenant)
            tenant = tenant.id
            cliente = cadastro_de_cliente.objects.get(razao_social=cliente)
            cliente = cliente.id
            banco = BancosCliente.objects.get(banco=banco)
            banco = banco.id

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

            # Criar o autômato Aho-Corasick
            A = ahocorasick.Automaton()
            regras = Regra.objects.for_tenant(tenant).filter(cliente_id=cliente).select_related('categoria',
                                                                                                     'subcategoria',
                                                                                                     'centrodecusto')
            for idx, regra in enumerate(regras):
                A.add_word(str(regra.descricao).upper(),
                           (idx, regra))  # Adiciona as descrições das regras no autômato
            A.make_automaton()  # Compila o autômato para otimizar a pesquisa

            movimentacoes_to_create = []  # Lista para armazenar as movimentações que serão criadas
            transicoes_to_create = []  # Lista para armazenar as transições que serão criadas
            conciliados = 0  # Contador para o número de movimentações conciliadas

            # Processamento das transações
            for dado in dados:
                descricao = dado['descricao'].upper()

                # Verifica se já existe uma movimentação com a mesma data, descrição e valor
                if MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente_id=cliente, banco_id=banco,
                                                                                  data=dado['data'],
                                                                                  descricao=descricao,
                                                                                  valor=dado['valor']).exists():
                    a = MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente_id=cliente, banco_id=banco,
                                                                                       data=dado['data'],
                                                                                       descricao=descricao,
                                                                                       valor=dado['valor'])

                    continue  # Pula para o próximo dado se já existir uma movimentação igual

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

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


    return JsonResponse({'error': 'Método não permitido'}, status=405)



@csrf_exempt
def recice_webhook(request):
    webhook = request.body
    threading.Thread(target=process_webhook, args=(webhook,)).start()
    return JsonResponse({'status': 'success', 'message': 'Webhook received successfully'}, status=200)


def process_webhook(webhook):
    webhook = json.loads(webhook)
    event = webhook['event']

    if event == 'item/updated':

        # Criando acess_token
        url = "https://api.pluggy.ai/auth"

        payload = {
            "clientId": "226a2d88-095c-4469-9943-1a3e6e3ae477",
            "clientSecret": "58b103c9-2272-4f7d-a1ef-80dd015704dc"
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        api_key = response.text

        payload = {
            "clientId": "226a2d88-095c-4469-9943-1a3e6e3ae477",
            "clientSecret": "58b103c9-2272-4f7d-a1ef-80dd015704dc"
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-API-KEY": api_key
        }

        response = requests.post(url, json=payload, headers=headers)

        access_token = response.text
        access_token = json.loads(access_token)

        # Requisitando nome da conta
        itemId = webhook['itemId']

        url = f"https://api.pluggy.ai/items/{itemId}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": access_token['apiKey']
        }

        response = requests.get(url, headers=headers)

        banco = response.json()
        banco = str(banco['connector']['name'])

        # Requisitando dados da conta
        url = f"https://api.pluggy.ai/accounts"

        params = {"itemId": itemId,
                  "type": "BANK"}

        query_string = urlencode(params)
        url = f"{url}?{query_string}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": access_token['apiKey']
        }

        response = requests.get(url, headers=headers)

        dados_banco = response.json()

        transferNumber = dados_banco['results'][0]['bankData']['transferNumber']
        accountId = dados_banco['results'][0]['id']

        bancos = BancosCliente.objects.get(transferNumber=transferNumber)

        cliente = bancos.cliente
        tenant = bancos.tenant
        print(cliente)
        print(tenant)

        url = "https://api.pluggy.ai/transactions"

        to_date = date.today()
        from_date = to_date - timedelta(days=3)

        params = {"accountId": accountId,
                  "from": from_date,
                  "to": to_date,
                  }

        query_string = urlencode(params)
        url = f"{url}?{query_string}"

        headers = {
            "accept": "application/json",
            "X-API-KEY": access_token['apiKey']
        }

        response = requests.get(url, headers=headers)

        results = (response.json())
        print(results)
        results = results['results']

        dados = []

        tenant = Tenant.objects.get(nome=tenant)
        tenant = tenant.id
        cliente = cadastro_de_cliente.objects.get(razao_social=cliente)
        cliente = cliente.id
        banco = BancosCliente.objects.get(banco=banco)
        banco = banco.id

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

        # Criar o autômato Aho-Corasick
        A = ahocorasick.Automaton()
        regras = Regra.objects.for_tenant(tenant).filter(cliente_id=cliente).select_related('categoria',
                                                                                                 'subcategoria',
                                                                                                 'centrodecusto')
        for idx, regra in enumerate(regras):
            A.add_word(str(regra.descricao).upper(),
                       (idx, regra))  # Adiciona as descrições das regras no autômato
        A.make_automaton()  # Compila o autômato para otimizar a pesquisa

        movimentacoes_to_create = []  # Lista para armazenar as movimentações que serão criadas
        transicoes_to_create = []  # Lista para armazenar as transições que serão criadas
        conciliados = 0  # Contador para o número de movimentações conciliadas

        # Processamento das transações
        for dado in dados:
            descricao = dado['descricao'].upper()

            # Verifica se já existe uma movimentação com a mesma data, descrição e valor
            if MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente_id=cliente, banco_id=banco,
                                                                              data=dado['data'],
                                                                              descricao=descricao,
                                                                              valor=dado['valor']).exists():
                a = MovimentacoesCliente.objects.for_tenant(tenant).filter(cliente_id=cliente, banco_id=banco,
                                                                                   data=dado['data'],
                                                                                   descricao=descricao,
                                                                                   valor=dado['valor'])

                continue  # Pula para o próximo dado se já existir uma movimentação igual

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
                conciliados += 1  # Incrementa o contador de movimentações conciliadas
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

        print(f'Importação concluída. {conciliados} movimentações conciliadas.') # Retorna uma mensagem de sucesso
        return JsonResponse(
            data={'message': f'Importação concluída. {conciliados} movimentações conciliadas '},
            status=200)