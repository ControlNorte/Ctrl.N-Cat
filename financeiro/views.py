from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from cliente.models import cadastro_de_cliente
from .models import *
from .alteracoesdb import *
from .exibicoes import *
from datetime import *
from .teste import *
from django.http import JsonResponse
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from collections import defaultdict

# Create your views here.


@login_required
def financeiro_view(request):
    if request.tenant:
        clientes = cadastro_de_cliente.objects.for_tenant(request.tenant).filter(ativo=True).order_by('razao_social')
    else:
        clientes = "Sem Clientes Cadastrados"
    context = {'object_list': clientes}
    return render(request, 'homepagefinanceiro.html', context)


def financeirocliente(request, pk):
    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    request.session['dadoscliente'] = pk  # Armazena o pk na sessão
    if request.method == 'GET':
        dreresumo = dreresumida(cliente=dadoscliente)
    context = {'dadoscliente': dadoscliente, 'dreresumo': dreresumo}
    return render(request, 'financeirocliente.html', context)


def caixa(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    bancos = BancosCliente.objects.for_tenant(request.tenant).filter(ativo='True', cliente=dadoscliente).order_by('banco')
    context = {'dadoscliente': dadoscliente, 'bancos': bancos}
    return render(request, 'caixa.html', context)


@csrf_exempt
def movimentacao(request, banco):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    bancos = BancosCliente.objects.for_tenant(request.tenant).filter(ativo='True', cliente=dadoscliente).order_by('banco')
    bancoatual = BancosCliente.objects.for_tenant(request.tenant).get(ativo='True', cliente=dadoscliente, banco=banco)
    request.session['bancoatual'] = bancoatual.id
    mesatual = datetime.now().month
    mesatual = mes(mesatual)

    exbextrato = 'Não tem movimentações registradas nesse mês!'
    grafico = ''
    erroentrada = ''
    errosaida = ''
    df = ''
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        file = request.FILES['file']
        df = importar_arquivo_excel(file, cliente=dadoscliente, banco=bancoatual, request=request)

    if request.method == 'POST':
        dados = request.POST.dict()
        if dados.get('tipo') == 'mes':
            mesfiltro = messtr(dados.get('mesfiltro'))
            mesatual = dados.get('mesfiltro')
            grafico = gerar_grafico(cliente=dadoscliente, banco=bancoatual.id, mes=mesfiltro)
            exbextrato = extrato(cliente=dadoscliente, banco=bancoatual.id, mes=mesfiltro)

        elif dados.get('tipo') == 'entrada':
            valor = float(dados.get('valor').replace(',', '.'))

            if valor >= 0:
                movimentacoes = MovimentacoesCliente.objects.create(tenant=request.tenant,
                                                                    cliente=dadoscliente,
                                                                    banco=BancosCliente.objects.get(id=bancoatual.id),
                                                                    data=dados.get('data'),
                                                                    descricao=dados.get('descricao'),
                                                                    detalhe=dados.get('detalhe'),
                                                                    valor=valor,
                                                                    categoria=Categoria.objects.get(id=dados.get("categoria")),
                                                                    subcategoria=SubCategoria.objects.get(id=dados.get("subcategoria")),
                                                                    centrodecusto=CentroDeCusto.objects.get(id=dados.get("centrocusto")))
                movimentacoes.save()
                alteracaosaldo(banco=bancoatual.id, cliente=dadoscliente.id, data=dados.get('data'), request=request)
            else:
                erroentrada = 'Valor de Entrada Tem que ser maior que 0'

        elif dados.get('tipo') == 'saida':
            if float(dados.get('valor').replace(',', '.')) <= 0:
                valor = float(dados.get('valor').replace(',', '.'))
            else:
                valor = float(dados.get('valor').replace(',', '.')) * - 1.0
            movimentacoes = MovimentacoesCliente.objects.create(tenant=request.tenant,
                                                                cliente=dadoscliente,
                                                                banco=BancosCliente.objects.get(id=bancoatual.id, cliente=dadoscliente),
                                                                data=dados.get('data'),
                                                                descricao=dados.get('descricao'),
                                                                detalhe=dados.get('detalhe'),
                                                                valor=valor,
                                                                categoria=Categoria.objects.get(
                                                                    id=dados.get("categoria"), cliente=dadoscliente),
                                                                subcategoria=SubCategoria.objects.get
                                                                (id=dados.get("subcategoria"), cliente=dadoscliente),
                                                                centrodecusto=CentroDeCusto.objects.get
                                                                (id=dados.get("centrocusto"), cliente=dadoscliente))
            movimentacoes.save()
            alteracaosaldo(banco=bancoatual.id, cliente=dadoscliente.id, data=dados.get('data'), request=request)

        elif dados.get('tipo') == 'transf':
            valor = float(dados.get('valor')) * -1.0
            saida = MovimentacoesCliente.objects.create(tenant=request.tenant,
                                                        cliente=dadoscliente,
                                                        banco=BancosCliente.objects.get(id=bancoatual.id, cliente=dadoscliente),
                                                        data=dados.get('data'),
                                                        descricao=dados.get('descricao'),
                                                        detalhe=dados.get('detalhe'),
                                                        valor=valor,
                                                        categoria=None,
                                                        subcategoria=None,
                                                        centrodecusto=None)
            saida.save()
            alteracaosaldo(banco=bancoatual.id, cliente=dadoscliente.id, data=dados.get('data'), request=request)
            entrada = MovimentacoesCliente.objects.create(tenant=request.tenant,
                                                          cliente=dadoscliente,
                                                          banco=BancosCliente.objects.get(id=dados.get('bancoentrada'), cliente=dadoscliente),
                                                          data=dados.get('data'),
                                                          descricao=dados.get('descricao'),
                                                          detalhe=dados.get('detalhe'),
                                                          valor=dados.get('valor'),
                                                          categoria=None,
                                                          subcategoria=None,
                                                          centrodecusto=None)
            entrada.save()
            bancoentrada = BancosCliente.objects.for_tenant(request.tenant).get(id=dados.get('bancoentrada'), cliente=dadoscliente)
            alteracaosaldo(banco=bancoentrada.id, cliente=dadoscliente.id, data=dados.get('data'), request=request)

    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    subcategorias = SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    centrodecustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    transicoes = TransicaoCliente.objects.for_tenant(request.tenant).filter(cliente=dadoscliente, banco=bancoatual).order_by('data')
    bancodestinos = BancosCliente.objects.for_tenant(request.tenant).filter(cliente=dadoscliente, ativo=True).order_by('banco')

    context = {'dadoscliente': dadoscliente, 'banco': bancoatual, 'categorias': categorias,
               'subcategorias': subcategorias, 'centrodecustos': centrodecustos, 'bancos': bancos, 'mesatual': mesatual,
               'exbextrato': exbextrato, 'erroentrada': erroentrada, 'errosaida': errosaida, 'form': form, 'df': df,
               'grafico': grafico, 'transicoes': transicoes, 'format_date': format_date,
               'format_currency': format_currency, 'bancodestinos': bancodestinos}

    return render(request, 'caixa.html', context)


def save_data(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)

    bancoatual = request.session.get('bancoatual')
    if not bancoatual:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    bancoatual = BancosCliente.objects.for_tenant(request.tenant).get(pk=bancoatual)

    movimentacoes_to_create = []
    if request.method == 'POST':
        cliente = dadoscliente  # Aqui, dadoscliente já é a instância correta de cadastro_de_cliente
        banco = bancoatual.id
        data = request.POST.get('data')
        data = datetime.strptime(data, '%d/%m/%Y').strftime('%Y-%m-%d')
        descricao = request.POST.get('descricao')
        categoria = request.POST.get('categoria')
        subcategoria = request.POST.get('subcategoria')
        detalhe = request.POST.get('detalhe')
        centrocusto = request.POST.get('centrocusto')
        valor = request.POST.get('valor')
        id = request.POST.get('id')
        valor = float(valor.replace('.', '').replace(',', '.'))

        try:
            movimentacoes_to_create.append(MovimentacoesCliente(
                        tenant=request.tenant,
                        cliente=cliente,
                        banco=BancosCliente.objects.get(id=banco),
                        data=data,
                        descricao=descricao,
                        detalhe=detalhe,
                        valor=valor,
                        categoria=Categoria.objects.get(id=categoria),
                        subcategoria=SubCategoria.objects.get(id=subcategoria),
                        centrodecusto=CentroDeCusto.objects.get(id=centrocusto)
            ))
        except:
            movimentacoes_to_create.append(MovimentacoesCliente(
                            tenant=request.tenant,
                            cliente=cliente,
                            banco=BancosCliente.objects.get(id=banco),
                            data=data,
                            descricao=descricao,
                            detalhe=detalhe,
                            valor=valor,
                            categoria=Categoria.objects.get(id=categoria),
                            subcategoria=SubCategoria.objects.get(id=subcategoria),
                            centrodecusto=None
            ))

        MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)
        if movimentacoes_to_create:
            for movimentacao in movimentacoes_to_create:
                alteracaosaldo(banco=banco, cliente=dadoscliente.id, data=movimentacao.data, request=request)
        TransicaoCliente.objects.for_tenant(request.tenant).get(id=id).delete()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def delete(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        TransicaoCliente.objects.for_tenant(request.tenant).get(id=id).delete()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def save_data_rule(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)

    bancoatual = request.session.get('bancoatual')
    if not bancoatual:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    bancoatual = BancosCliente.objects.for_tenant(request.tenant).get(pk=bancoatual)

    movimentacoes_to_create = []
    if request.method == 'POST':
        banco = bancoatual.id
        data = request.POST.get('data')
        id = request.POST.get('id')
        data = datetime.strptime(data, '%d/%m/%Y').strftime('%Y-%m-%d')
        descricao = request.POST.get('descricao')
        categoria = request.POST.get('categoria')
        subcategoria = request.POST.get('subcategoria')
        detalhe = request.POST.get('detalhe')
        centrocusto = request.POST.get('centrocusto')
        valor = request.POST.get('valor')
        valor = float(valor.replace('.', '').replace(',', '.'))
        regras = Regra.objects.create(tenant=request.tenant, cliente=dadoscliente, categoria=Categoria.objects.get(id=categoria, cliente=dadoscliente),
                                      subcategoria=SubCategoria.objects.get(id=subcategoria, cliente=dadoscliente),
                                      centrodecusto=CentroDeCusto.objects.get(id=centrocusto, cliente=dadoscliente),
                                      descricao=descricao, ativo=True)
        regras.save()
        try:
            movimentacoes_to_create.append(MovimentacoesCliente(
                        tenant=request.tenant,
                        cliente=dadoscliente,
                        banco=BancosCliente.objects.get(id=banco),
                        data=data,
                        descricao=descricao,
                        detalhe=detalhe,
                        valor=valor,
                        categoria=Categoria.objects.get(id=categoria),
                        subcategoria=SubCategoria.objects.get(id=subcategoria),
                        centrodecusto=CentroDeCusto.objects.get(id=centrocusto)
            ))
        except:
            movimentacoes_to_create.append(MovimentacoesCliente(
                            tenant=request.tenant,
                            cliente=dadoscliente,
                            banco=BancosCliente.objects.get(id=banco),
                            data=data,
                            descricao=descricao,
                            detalhe=detalhe,
                            valor=valor,
                            categoria=Categoria.objects.get(id=categoria),
                            subcategoria=SubCategoria.objects.get(id=subcategoria),
                            centrodecusto=None
            ))
        
        MovimentacoesCliente.objects.bulk_create(movimentacoes_to_create)

        for movimentacao in movimentacoes_to_create:
            alteracaosaldo(banco=banco, cliente=dadoscliente.id, data=str(movimentacao.data), request=request)

        TransicaoCliente.objects.for_tenant(request.tenant).get(id=id).delete()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def transf(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)

    bancoatual = request.session.get('bancoatual')
    if not bancoatual:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    bancoatual = BancosCliente.objects.for_tenant(request.tenant).get(pk=bancoatual)

    saida_to_create = []
    entrada_to_create = []
    if request.method == 'POST':
        cliente = dadoscliente
        banco = bancoatual.id
        id = request.POST.get('id')
        bancodestino = request.POST.get('bancodestino')
        data = request.POST.get('data')
        data = datetime.strptime(data, '%d/%m/%Y').strftime('%Y-%m-%d')
        descricao = request.POST.get('descricao')
        detalhe = request.POST.get('detalhe')
        valor = request.POST.get('valor')
        valor = float(valor.replace('.', '').replace(',', '.'))
        saida_to_create.append(MovimentacoesCliente(
                        tenant=request.tenant,
                        cliente=cliente,
                        banco=BancosCliente.objects.get(id=banco),
                        data=data,
                        descricao=descricao,
                        detalhe=detalhe,
                        valor=valor,
                        categoria=None,
                        subcategoria=None,
                        centrodecusto=None
        ))
        MovimentacoesCliente.objects.bulk_create(saida_to_create)
        for movimentacao in saida_to_create:
            alteracaosaldo(banco=banco, cliente=dadoscliente.id, data=movimentacao.data, request=request)
        valor = valor * -1.0
        nova_transf = MovimentacoesCliente.objects.for_tenant(request.tenant).filter(data=data, cliente=cliente, banco=bancodestino, valor=valor)
        if not nova_transf:
            entrada_to_create.append(MovimentacoesCliente(
                            tenant=request.tenant,
                            cliente=cliente,
                            banco=BancosCliente.objects.get(id=bancodestino),
                            data=data,
                            descricao=descricao,
                            detalhe=detalhe,
                            valor=valor,
                            categoria=None,
                            subcategoria=None,
                            centrodecusto=None
            ))

        MovimentacoesCliente.objects.bulk_create(entrada_to_create)
        for movimentacao in entrada_to_create:
            alteracaosaldo(banco=bancodestino, cliente=dadoscliente.id, data=movimentacao.data, request=request)
        TransicaoCliente.objects.for_tenant(request.tenant).get(id=id).delete()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def dre(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    cdcseleted = ''
    cdcseleted2 = ''
    anos = []
    for ano in range(2000, 2050):
        anos.append(ano)
    mes1 = '-'
    ano1 = '-'
    mes2 = mes(datetime.now().month)
    ano2 = datetime.now().year
    totcatmaeexb = 'Selecione os meses e anos para filtrar'
    dreexb = 'Selecione o ano para filtrar'
    if request.method == 'POST':
        dados = request.POST.dict()
        if dados.get('tipo') == 'comparacao':
            if dados.get('mes1') == '-' or dados.get('ano1') == '-':
                totcatmaeexb = 'Selecione os Mês 1 e Ano 1 para filtrar'
            else:
                mes1 = dados.get('mes1')
                ano1 = dados.get('ano1')
                mes2 = dados.get('mes2')
                ano2 = dados.get('ano2')
                mes1num = messtr(dados.get('mes1'))
                mes2num = messtr(dados.get('mes2'))

                if dados.get('centrodecusto') == 'None':
                    centrodecusto = None
                else:
                    centrodecusto = dados.get('centrodecusto')
                    cdcseleted2 = CentroDeCusto.objects.for_tenant(request.tenant).get(id=dados.get('centrodecusto'), cliente=dadoscliente)
                totcatmaeexb = drecomp(mes1=mes1num, ano1=dados.get('ano1'), mes2=mes2num,
                                         ano2=dados.get('ano2'), cliente=dadoscliente, centrocusto=centrodecusto)

        elif dados.get('tipo') == 'completa':
            if dados.get('centrodecusto') == 'None':
                dreexb = dreprincipal(cliente=dadoscliente, ano=dados.get('ano'))
            else:
                cdcseleted = CentroDeCusto.objects.for_tenant(request.tenant).get(id=dados.get('centrodecusto'), cliente=dadoscliente)
                dreexb = dreprincipal(cliente=dadoscliente, ano=dados.get('ano'),
                                      centrocusto=dados.get('centrodecusto'))

    centrodecustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')

    context = {'dadoscliente': dadoscliente, 'totcatmaeexb': totcatmaeexb, 'anos': anos, 'mes1': mes1, 'ano1': ano1,
               'mes2': mes2, 'ano2': ano2, 'dreexb': dreexb, 'centrodecustos': centrodecustos, 'cdcseleted': cdcseleted,
               'cdcseleted2': cdcseleted2}

    return render(request, 'dre.html', context)


def dashboard(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    context = {'dadoscliente': dadoscliente}
    return render(request, 'dashboard.html', context)


def orcamento(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    context = {'dadoscliente': dadoscliente}
    return render(request, 'orcamento.html', context)


def cadastrarorcamento(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    context = {'dadoscliente': dadoscliente}
    return render(request, 'cadastrarorcamento.html', context)


def contas(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    pesquisa = ''
    if request.method == 'POST':
        dados = request.POST.dict()
        id = dados.get('id') or None
        dt_i = dados.get('dt_i') or None
        dt_f = dados.get('dt_f') or None
        descricao = dados.get('descricao') or None
        detalhe = dados.get('detalhe') or None
        banco = dados.get('banco') or None
        centro_custo = dados.get('centro_custo') or None
        categoria = dados.get('categoria') or None
        sub_categoria = dados.get('sub_categoria') or None
        valor = dados.get('valor') or None
        tenant = request.tenant
        pesquisa, coisa = pesquisa_db(tenant, id=id, dt_i=dt_i, dt_f=dt_f, descricao=descricao, detalhe=detalhe, banco=banco,
                            centro_custo=centro_custo, categoria=categoria,
                            sub_categoria=sub_categoria, valor=valor)

        return pesquisa

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    movimentacoes = MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('id')
    paginator = Paginator(movimentacoes, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    subcategorias = SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    centrodecustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    bancos = BancosCliente.objects.for_tenant(request.tenant).filter(ativo='True', cliente=dadoscliente).order_by('banco')
    context = {'dadoscliente': dadoscliente, 'movimentacoes': movimentacoes, 'page_obj':page_obj, 'categorias': categorias, 
               'subcategorias': subcategorias, 'centrodecustos': centrodecustos, 'bancos': bancos, 'pesquisa': dadoscliente}
    return render(request, 'contas.html', context)


def maisopicoes(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    context = {'dadoscliente': dadoscliente}
    return render(request, 'maisopicoes.html', context)


def banco(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        dados = request.POST.dict()
        banco = BancosCliente.objects.create(tenant=request.tenant, cliente=dadoscliente, banco=dados.get("banco"),
                                             agencia=dados.get("agencia"),
                                             conta=dados.get("conta"), digito=dados.get("digito"),
                                             ativo=dados.get("ativo"))
        banco.save()
        return redirect('financeiro:banco')
    bancos = BancosCliente.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('banco')
    context = {'dadoscliente': dadoscliente, 'bancos': bancos}
    return render(request, 'banco.html', context)


def bancosaldo(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    banco = BancosCliente.objects.for_tenant(request.tenant).get(cliente=dadoscliente, id=id)
    if request.method == 'POST':
        dados = request.POST.dict()
        data = dados.get('data')
        saldofinal = float(dados.get("saldofinal"))
        Saldo.objects.update_or_create(
            data=data,
            banco=BancosCliente.objects.get(id=banco.id),
            cliente=dadoscliente,
            defaults={
                'saldoinicial': float(0.0),
                'saldofinal': float(saldofinal)
            }
        )
        saldodiario(banco=banco.id, cliente=dadoscliente, data=data, request=request)
        return redirect('financeiro:banco')
    context = {'dadoscliente': dadoscliente, 'banco': banco}
    return render(request, 'bancosaldo.html', context)


def editarbanco(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    bancoeditado = BancosCliente.objects.for_tenant(request.tenant).get(cliente=dadoscliente, id=id)
    bancos = BancosCliente.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('banco')
    if request.method == 'POST':
        bancoeditado.banco = request.POST.get('banco')
        bancoeditado.agencia = request.POST.get('agencia')
        bancoeditado.conta = request.POST.get('conta')
        bancoeditado.digito = request.POST.get('digito')

        # Verifica o checkbox
        bancoeditado.ativo = True if request.POST.get('ativo') else False

        # Salva as alterações no banco de dados
        bancoeditado.save()

        return redirect('financeiro:banco')
    context = {'dadoscliente': dadoscliente, 'bancos': bancos, 'bancoeditado': bancoeditado}
    return render(request, 'editarbanco.html', context)


def categoria(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        dados = request.POST.dict()
        categoriamae = CategoriaMae.objects.get(id=dados.get("categoriamae"))
        nome = dados.get("nome")

        # Verificação se já existe uma categoria com o mesmo cliente, categoriamae e nome
        if Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente, categoriamae=categoriamae, nome=nome).exists():
            messages.error(request, "Categoria já cadastrada")
        else:
            categoria = Categoria.objects.create(tenant=request.tenant, cliente=dadoscliente, categoriamae=categoriamae, nome=nome)
            categoria.save()

    categoriasmae = CategoriaMae.objects.all()
    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    context = {
        'dadoscliente': dadoscliente,
        'categorias': categorias,
        'categoriasmae': categoriasmae
    }
    return render(request, 'categoria.html', context)


def editarcategoria(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    categoriaeditada = Categoria.objects.for_tenant(request.tenant).get(cliente=dadoscliente, id=id)
    if request.method == 'POST':
        categoriaeditada.categoriamae = CategoriaMae.objects.get(nome=request.POST.get('categoriamae'))
        categoriaeditada.nome = request.POST.get('nome')

        categoriaeditada.save()

        return redirect('financeiro:categoria')
    categoriasmae = CategoriaMae.objects.all().order_by('nome')
    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    context = {'dadoscliente': dadoscliente, 'categorias': categorias, 'categoriasmae': categoriasmae,
               'categoriaeditada': categoriaeditada}
    return render(request, 'editarcategoria.html', context)


def subcategoria(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        dados = request.POST.dict()
        categoria = Categoria.objects.for_tenant(request.tenant).get(id=dados.get("categoria"), cliente=dadoscliente)
        nome = dados.get("nome")

        # Verificação se já existe uma subcategoria com o mesmo cliente, categoria e nome
        if SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente, categoria=categoria, nome=nome).exists():
            messages.error(request, "Sub-categoria já cadastrada")
        else:
            subcategoria = SubCategoria.objects.create(tenant=request.tenant, cliente=dadoscliente, categoria=categoria, nome=nome)
            subcategoria.save()

    categoriasmae = CategoriaMae.objects.all().order_by('nome')
    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    subcategorias = SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    context = {
        'dadoscliente': dadoscliente,
        'categorias': categorias,
        'categoriasmae': categoriasmae,
        'subcategorias': subcategorias
    }
    return render(request, 'subcategoria.html', context)


def editarsubcategoria(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    subcategoriaeditada = SubCategoria.objects.for_tenant(request.tenant).get(cliente=dadoscliente, id=id)
    if request.method == 'POST':
        subcategoriaeditada.categoria = Categoria.objects.for_tenant(request.tenant).get(nome=request.POST.get('categoria'), cliente=dadoscliente)
        subcategoriaeditada.nome = request.POST.get('nome')

        subcategoriaeditada.save()

        return redirect('financeiro:subcategoria')
    categoriasmae = CategoriaMae.objects.all().order_by('nome')
    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    subcategorias = SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    context = {'dadoscliente': dadoscliente, 'categorias': categorias, 'categoriasmae': categoriasmae, 'subcategorias':
        subcategorias, 'subcategoriaeditada': subcategoriaeditada}
    return render(request, 'editarsubcategoria.html', context)


def centrocusto(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        dados = request.POST.dict()
        nome = dados.get("nome")
        ativo = dados.get("ativo")

        # Verificação se já existe um centro de custo com o mesmo cliente e nome
        if CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente, nome=nome).exists():
            messages.error(request, "Centro de Custo já cadastrado")
        else:
            centrocusto = CentroDeCusto.objects.create(tenant=request.tenant, cliente=dadoscliente, nome=nome, ativo=ativo)
            centrocusto.save()

    centrocustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    context = {'dadoscliente': dadoscliente, 'centrocustos': centrocustos}
    return render(request, 'centrocusto.html', context)


def editarcentrocusto(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    centrocustoeditado = CentroDeCusto.objects.for_tenant(request.tenant).get(cliente=dadoscliente, id=id)
    if request.method == 'POST':
        centrocustoeditado.nome = request.POST.get('nome')
        centrocustoeditado.ativo = True if request.POST.get('ativo') else False

        centrocustoeditado.save()

        return redirect('financeiro:centrocusto')
    centrocustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    context = {'dadoscliente': dadoscliente, 'centrocustos': centrocustos, 'centrocustoeditado': centrocustoeditado}
    return render(request, 'editarcentrocusto.html', context)


def editarregra(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    regraeditada = Regra.objects.for_tenant(request.tenant).get(cliente=dadoscliente, id=id)

    if request.method == 'POST':
        dados = request.POST.dict()
        Regra.objects.for_tenant(request.tenant).filter(id=id, cliente=dadoscliente).update(
            cliente=dadoscliente,
            categoria=Categoria.objects.get(nome=dados.get("categoria"), cliente=dadoscliente),
            subcategoria=SubCategoria.objects.get(nome=dados.get("subcategoria"), cliente=dadoscliente),
            centrodecusto=CentroDeCusto.objects.get(nome=dados.get("centrodecusto"), cliente=dadoscliente),
            descricao=dados.get("descricao"),
            ativo=dados.get("ativo")
        )

    # Obtém todas as regras do cliente
    regras = Regra.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('categoria')

    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    subcategorias = SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    centrodecustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')

    context = {
        'dadoscliente': dadoscliente,
        'regraeditada': regraeditada,
        'categorias': categorias,
        'subcategorias': subcategorias,
        'centrodecustos': centrodecustos,
        'regras': regras
    }
    return render(request, 'editarregra.html', context)


def regra(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        dados = request.POST.dict()
        
        # Verifica se já existe um cadastro com os mesmos dados
        existe_regra = Regra.objects.for_tenant(request.tenant).filter(
            cliente=dadoscliente,
            categoria_id=dados.get("categoria"),
            subcategoria_id=dados.get("subcategoria"),
            centrodecusto_id=dados.get("centrodecusto"),
            descricao=dados.get("descricao"),
        ).exists()

        if existe_regra:
            messages.error(request, "Centro de Custo já cadastrado")
            
        else:
            # Cria o novo registro
            regras = Regra.objects.create(tenant=request.tenant,
                cliente=dadoscliente,
                categoria=Categoria.objects.get(id=dados.get("categoria"), cliente=dadoscliente),
                subcategoria=SubCategoria.objects.get(id=dados.get("subcategoria"), cliente=dadoscliente),
                centrodecusto=CentroDeCusto.objects.get(id=dados.get("centrodecusto"), cliente=dadoscliente),
                descricao=dados.get("descricao"),
                ativo=dados.get("ativo")
            )
            regras.save()

    categorias = Categoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    subcategorias = SubCategoria.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    centrodecustos = CentroDeCusto.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('nome')
    regras = Regra.objects.for_tenant(request.tenant).filter(cliente=dadoscliente).order_by('categoria')

    context = {'dadoscliente': dadoscliente, 'categorias': categorias, 'subcategorias': subcategorias,
               'centrodecustos': centrodecustos, 'regras': regras}
    return render(request, 'regra.html', context)


def get_movimentacao(request, id):
    try:
        movimentacao = MovimentacoesCliente.objects.for_tenant(request.tenant).get(pk=id)
        global data_ant
        data_ant = movimentacao.data
        data = {
            'id': movimentacao.id,
            'data': movimentacao.data,
            'descricao': movimentacao.descricao,
            'detalhe': movimentacao.detalhe,
            'banco': movimentacao.banco.banco if movimentacao.banco else None,
            'centrodecusto': movimentacao.centrodecusto.nome if movimentacao.centrodecusto else None,
            'categoria': movimentacao.categoria.nome if movimentacao.categoria else None,
            'subcategoria': movimentacao.subcategoria.nome if movimentacao.subcategoria else None,
            'valor': movimentacao.valor,
        }
        return JsonResponse(data)
    except MovimentacoesCliente.DoesNotExist:
        return JsonResponse({'error': 'Movimentação não encontrada'}, status=404)


def edit_movimentacao(request):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        id = request.POST.get('id')
        movimentacao = get_object_or_404(MovimentacoesCliente, id=id)
        movimentacao.descricao = request.POST.get('descricao')
        movimentacao.detalhe = request.POST.get('detalhe')
        movimentacao.data = request.POST.get('data')
        
        banco_id = request.POST.get('banco')
        centrodecusto_id = request.POST.get('centrocusto')
        categoria_id = request.POST.get('categoria')
        subcategoria_id = request.POST.get('subcategoria')
        
        try:
            movimentacao.banco = BancosCliente.objects.for_tenant(request.tenant).get(id=banco_id)
        except ObjectDoesNotExist:
            return JsonResponse({'success': False, 'error': 'Banco não encontrado'})
        
        # Definindo centrodecusto como None se o valor for uma string vazia
        if centrodecusto_id == '':
            movimentacao.centrodecusto = None
        else:
            try:
                movimentacao.centrodecusto = CentroDeCusto.objects.for_tenant(request.tenant).get(id=centrodecusto_id)
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Centro de custo não encontrado'})
        
        try:
            movimentacao.categoria = Categoria.objects.for_tenant(request.tenant).get(id=categoria_id)
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Categoria não encontrada'})
        
        try:
            movimentacao.subcategoria = SubCategoria.objects.for_tenant(request.tenant).get(id=subcategoria_id)
        except ObjectDoesNotExist:
            return JsonResponse({'error': 'Subcategoria não encontrada'})
        
        try:
            movimentacao.valor = float(request.POST.get('valor'))  # Converte o valor para float
        except ValueError:
            return JsonResponse({'error': 'Valor inválido'})
        
        data1 = datetime.strptime(request.POST.get('data'), '%Y-%m-%d').date()
        data2 = data1.strftime('%Y-%m-%d')

        if data1 < data_ant:
            data = data2
        else:
            data = str(data_ant)

        movimentacao.save()
        alteracaosaldo(banco=banco_id, cliente=dadoscliente.id, data=data, request=request)

        return redirect('financeiro:contas')

    return JsonResponse({'success': False})


def delete_movimentacao(request, id):
    pk = request.session.get('dadoscliente')
    if not pk:
        return redirect('alguma_view_de_erro')  # Redireciona se dadoscliente não estiver disponível

    dadoscliente = cadastro_de_cliente.objects.for_tenant(request.tenant).get(pk=pk)
    if request.method == 'POST':
        try:
            movimentacao = MovimentacoesCliente.objects.for_tenant(request.tenant).get(pk=id)
            data = str(movimentacao.data)
            banco = movimentacao.banco
            movimentacao.delete()
            alteracaosaldo(banco=banco.id, cliente=dadoscliente.id, data=str(data), request=request)
            return JsonResponse({'success': True})
        except MovimentacoesCliente.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Movimentação não encontrada'}, status=404)
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)
