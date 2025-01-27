from IPython.terminal.shortcuts.filters import pass_through
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import BancosCliente, cadastro_de_cliente
import requests, json
from urllib.parse import urlencode

@csrf_exempt  # Use apenas para testes; idealmente, configure o CSRF corretamente.
def handle_item_data(request):
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
    print(access_token)
    print(itemId)

    if request.method == 'POST':
        try:
            # Lista de contas

            url = f"https://api.pluggy.ai/accounts"

            params = {"itemId": itemId}

            query_string = urlencode(params)
            url = f"{url}?{query_string}"

            headers = {
                "accept": "application/json",
                "X-API-KEY": access_token['apiKey']
            }

            response = requests.get(url, headers=headers)

            print(response.text)


            # # Criando banco no banco de dados
            # pk = request.session.get('dadoscliente')
            # if not pk:
            #     print("sem pk")
            # dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
            # banco = BancosCliente.objects.create(tenant=request.tenant, cliente=dadoscliente, banco=dados.get("banco"),
            #                                      agencia=dados.get("agencia"),
            #                                      conta=dados.get("conta"), digito=dados.get("digito"),
            #                                      ativo=dados.get("ativo")) ## criar accountId no bd para conseguir pular uma estapa
            # banco.save()



            # Retorna uma resposta de sucesso
            return JsonResponse({'message': 'Dados recebidos com sucesso!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método não permitido'}, status=405)