from django.shortcuts import render, reverse, HttpResponseRedirect
from .models import *
from django.views.generic import TemplateView, ListView, DetailView, FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import Cadastrodeclientes
from django.http import FileResponse
import openpyxl
from io import BytesIO
from django.db import transaction
from django.shortcuts import redirect
from django.contrib import messages
import pandas as pd
from django.http import JsonResponse


# Create your views here.
# def cliente(request):
#     return render(request,'cliente.html')

class Cliente(LoginRequiredMixin, ListView):
    template_name = 'cliente.html'
    model = cadastro_de_cliente

    def get_queryset(self):
        termo_pesquisa = self.request.GET.get('query')
        if termo_pesquisa:
            object_list = self.model.objects.filter(razao_social__icontains=termo_pesquisa)
            return object_list
        else:
            return self.model.objects.all


class Destalhesclientes(LoginRequiredMixin, DetailView):
    template_name = 'detalhesclientes.html'
    model = cadastro_de_cliente
    context_object_name = 'cliente'


def cadastrarcliente(request):
    if request.method == 'POST':
        dados = request.POST.dict()
        novocliente = cadastro_de_cliente.objects.create(razao_social=dados.get('razao'), cnpj=dados.get('cnpj'),
                                                        logadouro=dados.get('logadouro'),bairro=dados.get('bairro'),
                                                        número=dados.get('número'), cidade=dados.get('cidade'),
                                                        estado=dados.get('estado'), pessoa_de_contato=dados.get('pessoa'),
                                                        telefone=dados.get('telefone'), email_contato=dados.get('email'),
                                                        ramo=Ramo.objects.get(id=dados.get('ramo')), ativo=dados.get('ativo'),
                                                        bancos_utilizados=dados.get('bancos'),
                                                        servicos_contratados=dados.get('servicos'),
                                                        responsavel_conciliacao=dados.get('conciliacao'),
                                                        responsavel_apresentacao=dados.get('apresentacao'),
                                                        funcionarios=dados.get('funcionarios'),
                                                        contas_fixas=dados.get('fixas'),
                                                        classificacoes=dados.get('classificacoes'),
                                                        principais_fornecedores=dados.get('fornecedores'),
                                                        observacoes=dados.get('observacoes'),
                                                        sugestoes=dados.get('sugestoes'),
                                                        historico=dados.get('historico'))
        novocliente.save()

    ramos = Ramo.objects.all()

    context = {'ramos': ramos}

    return render(request, 'cadastrarcliente.html', context)

class Cadastrarcliente(LoginRequiredMixin, FormView):
    form_class = Cadastrodeclientes
    template_name = 'cadastrarcliente.html'

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('cliente:cliente')


class Editarcliente(LoginRequiredMixin, UpdateView):
    template_name = 'editarcliente.html'
    model = cadastro_de_cliente
    fields = '__all__'

    def get_success_url(self):
        return reverse('cliente:cliente')


def download_modelo_importacao_cadastro_cliente(request):
    # Criar um arquivo Excel em memória
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Modelo de Importação"

    # Obter os campos do model CadastroClientes
    fields = [field.name for field in cadastro_de_cliente._meta.fields]
    # Verificando se o campo existe antes de remover
    for field in ['id', 'tenant', 'historico', 'criado_em']:
        if field in fields:
            fields.remove(field)
    # Escrever os nomes dos campos na primeira linha
    for col_num, field in enumerate(fields, 1):
        ws.cell(row=1, column=col_num, value=field)

    # Salvar o arquivo Excel em memória
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Retornar o arquivo como resposta para download
    return FileResponse(output, as_attachment=True, filename='modelo_importacao_clientes.xlsx')


def importar_clientes(request):
    if request.method == "POST" and request.FILES['file']:
        excel_file = request.FILES['file']

        try:
            # Ler o arquivo Excel usando pandas
            df = pd.read_excel(excel_file)

            # Converter DataFrame para lista de dicionários
            registros = df.to_dict(orient='records')

            # Lista para armazenar os objetos do model
            clientes = []
            razao_social = ''
            cnpj = ''
            logadouro = ''
            numero = ''
            bairro = ''
            cidade = ''
            estado = ''
            pessoa_contato = ''
            telefone = ''
            email = ''

            # Criar objetos de CadastroClientes com base nos registros
            for registro in registros:
                if registro.get('razao_social'):
                    razao_social = registro.get('razao_social')
                else:
                    return JsonResponse({'error': 'Razão Social não encontrada'})

                if registro.get('cnpj'):
                    cnpj = registro.get('cnpj')
                else:
                    return JsonResponse({'error': 'CNPJ não encontrado'})

                if registro.get('logadouro'):
                    logadouro = registro.get('logadouro')
                else:
                    return JsonResponse({'error': 'Logadouro não encontrado'})

                if registro.get('numero'):
                    numero = registro.get('numero')
                else:
                    return JsonResponse({'error': 'Numero não encontrado'})

                if registro.get('bairro'):
                    bairro = registro.get('bairro')
                else:
                    return JsonResponse({'error': 'Bairro não encontrado'})

                if registro.get('cidade'):
                    cidade = registro.get('cidade')
                else:
                    return JsonResponse({'error': 'Cidade não encontrado'})

                if registro.get('estado'):
                    estado = registro.get('estado')
                else:
                    return JsonResponse({'error': 'Estado não encontrado'})

                if registro.get('pessoa_contato'):
                    pessoa_contato = registro.get('pessoa_contato')
                else:
                    return JsonResponse({'error': 'Pessoa de Contato não encontrada'})

                if registro.get('telefone'):
                    telefone = registro.get('telefone')
                else:
                    return JsonResponse({'error': 'Telefone não encontrado'})

                if registro.get('email'):
                    email = registro.get('email')
                else:
                    return JsonResponse({'error': 'E-mail não encontrado'})

                cliente = cadastro_de_cliente(
                    razao_social=razao_social,
                    cnpj=cnpj,
                    logadouro=logadouro,
                    numero=numero,
                    bairro=bairro,
                    cidade=cidade,
                    estado=estado,
                    pessoa_contato=pessoa_contato,
                    telefone=telefone,
                    email=email,
                    bancos=registro.get('bancos'),
                    servicos=registro.get('servicos'),
                    conciliacao=registro.get('conciliacao'),
                    reunioes=registro.get('reunioes'),
                    funcionarios=registro.get('funcionarios'),
                    contas_fixas=registro.get('contas_fixas'),
                    classificacoes=registro.get('classificacoes'),
                    fornecedores=registro.get('fornecedores'),
                    observacoes=registro.get('observacoes'),
                    sugestoes=registro.get('sugestoes'),
                    historico=registro.get('historico'),
                    ativo=registro.get('ativo') == 'Sim'  # Converter "Sim" ou "Não" para booleano
                )
                clientes.append(cliente)

            # Salvar os dados no banco de dados em uma transação atômica
            with transaction.atomic():
                cadastro_de_cliente.objects.bulk_create(clientes)

            messages.success(request, "Clientes importados com sucesso!")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao importar: {e}")
            return redirect('nome_da_view')

    return redirect('nome_da_view')
