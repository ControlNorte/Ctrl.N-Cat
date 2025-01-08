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
            else:
                JsonResponse({'error': 'Razão Social não encontrada'})

            if registro.get('cnpj'):
                cnpj = registro.get('cnpj')
            else:
                JsonResponse({'error': 'CNPJ não encontrado'})

            if registro.get('logadouro'):
                logadouro = registro.get('logadouro')
            else:
                JsonResponse({'error': 'Logadouro não encontrado'})

            if registro.get('numero'):
                numero = registro.get('numero')
            else:
                JsonResponse({'error': 'Numero não encontrado'})

            if registro.get('bairro'):
                bairro = registro.get('bairro')
            else:
                JsonResponse({'error': 'Bairro não encontrado'})

            if registro.get('cidade'):
                cidade = registro.get('cidade')
            else:
                JsonResponse({'error': 'Cidade não encontrado'})

            if registro.get('estado'):
                estado = registro.get('estado')
            else:
                JsonResponse({'error': 'Estado não encontrado'})

            if registro.get('pessoa_contato'):
                pessoa_contato = registro.get('pessoa_contato')
            else:
                JsonResponse({'error': 'Pessoa de Contato não encontrada'})

            if registro.get('telefone'):
                telefone = registro.get('telefone')
            else:
                JsonResponse({'error': 'Telefone não encontrado'})

            if registro.get('email'):
                email = registro.get('email')
            else:
                JsonResponse({'error': 'E-mail não encontrado'})

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

        messages.success("Clientes importados com sucesso!")
    except Exception as e:
        messages.error(f"Ocorreu um erro ao importar: {e}")

    return print('Clientes salvos com Sucesso')
