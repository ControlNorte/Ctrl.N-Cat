from django.shortcuts import render, reverse, HttpResponseRedirect
from .models import *
from django.views.generic import TemplateView, ListView, DetailView, FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import Cadastrodeclientes


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

    context = {'ramos':ramos}

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
