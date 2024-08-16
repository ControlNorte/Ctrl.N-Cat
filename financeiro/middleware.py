from cliente.models import cadastro_de_cliente


class ClienteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Código para rodar antes da view ser chamada
        response = self.get_response(request)
        # Código para rodar após a view ser chamada
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Código para rodar antes da view ser chamada
        if 'pk' in view_kwargs:
            request.dadoscliente = cadastro_de_cliente.objects.get(pk=view_kwargs['pk'])