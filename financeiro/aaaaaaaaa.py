import pandas as pd
from .models import Regra


# Conexão com o banco de dados
caminho_arquivo = r'C:\Users\Dell\Documents\Nova Pasta\arquivo.xlsx'
dados = pd.read_excel(caminho_arquivo)
regras = Regra.objects.filter(cliente=2)

for regra in regras:
    print(regra.descricao)

# dados['Data'] = pd.to_datetime(dados['Data'])  # Certifique-se de que a coluna 'Data' esteja no formato datetime
# dados = dados.to_dict('records')
