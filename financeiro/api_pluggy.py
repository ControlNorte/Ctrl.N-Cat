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

            # Lista de contas
            url = f"https://api.pluggy.ai/accounts?itemId={itemId}"

            headers = {"accept": "application/json"}

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
            #                                      ativo=dados.get("ativo"))
            # banco.save()



            # Retorna uma resposta de sucesso
            return JsonResponse({'message': 'Dados recebidos com sucesso!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método não permitido'}, status=405)