from IPython.terminal.shortcuts.filters import pass_through
from dask.array import empty
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import BancosCliente, cadastro_de_cliente
import requests, json, re
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
            if response.status_code == 200:
                print("certo")
            else:
                print('erro')

            dados_banco = response.json()
            print(dados_banco)
            dados_banco = dados_banco['results'][0]['number']

            # Pegar o primeiro número
            first_number = dados_banco

            # Separar usando regex
            separated_parts = re.split(r'[/-]', first_number)

            # Atribuir às variáveis
            agencia = separated_parts[0]
            conta = separated_parts[1]
            digito = separated_parts[2]

            # Criando banco no banco de dados
            pk = request.session.get('dadoscliente')
            if not pk:
                print("sem pk")
            dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)

            banco = BancosCliente.objects.filter(tenant=request.tenant, cliente=dadoscliente, banco=banco,
                                                 agencia=agencia, conta=conta, digito=digito,)
            if banco is empty:
                banco = BancosCliente.objects.create(tenant=request.tenant, cliente=dadoscliente, banco=banco,
                                                 agencia=agencia, conta=conta, digito=digito, ativo=True)
                banco.save()

            # Retorna uma resposta de sucesso
            return JsonResponse({'message': 'Dados recebidos com sucesso!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método não permitido'}, status=405)