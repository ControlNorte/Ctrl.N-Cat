import pandas as pd
from django import forms
from django.http import JsonResponse
from django.db import transaction
from .models import cadastro_de_cliente
from django.contrib import messages

from financeiro.models import UploadedFile

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']


def importar_clientes(arquivo_importacao_cliente, tenant):

    if not arquivo_importacao_cliente:
        print("Erro: Nenhum arquivo foi selecionado.")  # Retorna erro se nenhum arquivo foi selecionado

    print(tenant)
    try:
        # Ler o arquivo Excel usando pandas
        df = pd.read_excel(arquivo_importacao_cliente)

        # Converter DataFrame para lista de dicionários
        registros = df.to_dict(orient='records')

        # Lista para armazenar os objetos do model
        cliente = ''
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
                print(razao_social)
            else:
                JsonResponse({'error': 'Razão Social não encontrada'})

            if registro.get('cnpj'):
                cnpj = registro.get('cnpj')
                print(cnpj)
            else:
                JsonResponse({'error': 'CNPJ não encontrado'})

            if registro.get('logadouro'):
                logadouro = registro.get('logadouro')
                print(logadouro)

            if registro.get('numero'):
                numero = registro.get('numero')
                print(numero)

            if registro.get('bairro'):
                bairro = registro.get('bairro')
                print(bairro)

            if registro.get('cidade'):
                cidade = registro.get('cidade')
                print(cidade)

            if registro.get('estado'):
                estado = registro.get('estado')
                print(estado)

            if registro.get('pessoa_contato'):
                pessoa_contato = registro.get('pessoa_contato')
                print(pessoa_contato)

            if registro.get('telefone'):
                telefone = registro.get('telefone')
                print(telefone)

            if registro.get('email'):
                email = registro.get('email')
                print(email)

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
                    ativo=registro.get('ativo') == 'Sim',  # Converter "Sim" ou "Não" para booleano
                    tenant=tenant,
                )

        clientes.append(cliente)

        # Salvar os dados no banco de dados em uma transação atômica
        with transaction.atomic():
            cadastro_de_cliente.objects.bulk_create(clientes)

        print('Clientes salvos com Sucesso')

    except:
        print('Erro')

    return print('Importação finalizado')
