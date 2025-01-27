from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt  # Use apenas para testes; idealmente, configure o CSRF corretamente.
def handle_item_data(request):
    if request.method == 'POST':
        try:
            # Converte o corpo da requisição JSON em dicionário Python
            data = json.loads(request.body)

            # Processa o itemData (por exemplo, salvando no banco de dados)
            print("Item Data recebido:", data)

            # Retorna uma resposta de sucesso
            return JsonResponse({'message': 'Dados recebidos com sucesso!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Método não permitido'}, status=405)