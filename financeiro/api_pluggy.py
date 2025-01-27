from IPython.terminal.shortcuts.filters import pass_through
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import BancosCliente, cadastro_de_cliente
import requests


@csrf_exempt  # Use apenas para testes; idealmente, configure o CSRF corretamente.
def handle_item_data(request):
    if request.method == 'POST':
        try:
            # Converte o corpo da requisição JSON em dicionário Python
            data = json.loads(request.body)

            # Processa o itemData (por exemplo, salvando no banco de dados)
            print("Item Data recebido:", data)

            itemId= data['item']['id']

            print(itemId)

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

            api_Key = response.text

            url = "https://api.pluggy.ai/connect_token"

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "X-API-KEY": api_Key
            }

            response = requests.post(url, headers=headers)

            acesse_Token = response.text
            print(acesse_Token)

            # Lista de contas
            url = f"https://api.pluggy.ai/accounts?itemId={itemId}"

            headers = {
                "accept": "application/json",
                "X-API-KEY": api_Key
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