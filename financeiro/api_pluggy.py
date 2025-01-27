from IPython.terminal.shortcuts.filters import pass_through
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import BancosCliente, cadastro_de_cliente
import requests, json, re
from urllib.parse import urlencode

@csrf_exempt  # Use apenas para testes; idealmente, configure o CSRF corretamente.
def handle_item_data(request):

    pk = request.session.get('dadoscliente')
    if not pk:
        return print('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    print(dadoscliente)

    # Converte o corpo da requisição JSON em dicionário Python
    data = json.loads(request.body)

    itemId = data['item']['id']

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
    print(access_token['apiKey'])
    print(itemId)

    if request.method == 'POST':
        try:
            # Lista de contas
            url = f"https://api.pluggy.ai/accounts"

            params = {"itemId": itemId,
                      "type": "BANK"}

            query_string = urlencode(params)
            url = f"{url}?{query_string}"
            print(url)
            headers = {
                "accept": "application/json",
                "X-API-KEY": access_token['apiKey']
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print(response.json())
            else:
                print('erro')

            dados_banco = response.json()
            dados_banco = dados_banco['results'][0]['number']
            print(dados_banco)

            # Pegar o primeiro número
            first_number = dados_banco

            # Separar usando regex
            separated_parts = re.split(r'[/-]', first_number)

            # Atribuir às variáveis
            agencia = separated_parts[0]
            conta = separated_parts[1]
            digito = separated_parts[2]

            print(f"Agência: {agencia}")
            print(f"Conta: {conta}")
            print(f"Dígito: {digito}")
            print(itemId)
            # # Criando banco no banco de dados
            # pk = request.session.get('dadoscliente')
            # if not pk:
            #     print("sem pk")
            # dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
            # banco = BancosCliente.objects.create(tenant=request.tenant, cliente=dadoscliente, banco="teste1",
            #                                      agencia=agencia,
            #                                      conta=conta, digito=digito,
            #                                      ativo=True ## criar accountId no bd para conseguir pular uma estapa
            # banco.save()



            # Retorna uma resposta de sucesso
            return JsonResponse({'message': 'Dados recebidos com sucesso!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método não permitido'}, status=405)