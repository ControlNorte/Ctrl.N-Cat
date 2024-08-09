import pandas as pd
import sqlite3
from .teste import *
from datetime import *
from jinja2 import Template
import plotly.express as px
import io
import base64
import plotly.graph_objects as go
import psycopg2
from sqlalchemy import create_engine

# EXTRATO NO HTML: caixa.html


def formatar_valor(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def extrato(cliente, banco, mes):
    try:
        # Conectar ao banco de dados PostgreSQL
        db_url = "postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
        engine = create_engine(db_url)

        # Ler tabelas do banco de dados
        with engine.connect() as conexao:
            tabela = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)
            tabela0 = pd.read_sql("SELECT * FROM financeiro_saldo", conexao)

        # Filtrar e preparar a tabela
        tabela = tabela[(tabela['cliente_id'] == cliente.id) & (tabela['banco_id'] == banco)]
        tabela['data'] = pd.to_datetime(tabela['data'], format='ISO8601')
        tabela['mes'] = tabela['data'].dt.month
        tabela = tabela[tabela['mes'] == mes]
        tabela = tabela[['data', 'descricao', 'valor']].sort_values('data')

        datastabela = tabela[['data']].drop_duplicates()['data']

        if datastabela.empty:
            return 'Selecione o mês para filtrar'

        # Preparar tabela0
        tabela0['data'] = pd.to_datetime(tabela0['data'], format='ISO8601')
        tabela0['mes'] = tabela0['data'].dt.month
        tabela0['ano'] = tabela0['data'].dt.year
        tabela0 = tabela0.sort_values('data')

        ano = datastabela.iloc[0].year
        if mes == 1:
            mes = 12
            ano -= 1
        else:
            mes -= 1

        saldoinicial = tabela0[(tabela0['ano'] == ano) & (tabela0['mes'] == mes) & (tabela0['banco_id'] == banco) &
                               (tabela0['cliente_id'] == cliente.id)]

        if saldoinicial.empty:
            datas = []
            descricao = []
            valor = []
        else:
            saldoinicialdata = saldoinicial['data'].iloc[-1]
            saldoinicialvalor = saldoinicial['saldofinal'].iloc[-1]
            datas = [saldoinicialdata]
            descricao = ['SALDO INICIAL']
            valor = [saldoinicialvalor]

        for data in datastabela:
            descricao.append('SALDO')
            datas.append(data)
            tabela0_filtered = tabela0[(tabela0['cliente_id'] == cliente.id) & (tabela0['banco_id'] == banco)]
            tabela0_filtered = tabela0_filtered.sort_values('data').set_index('data')
            saldofinal = tabela0_filtered.at[data, 'saldofinal']
            valor.append(float(saldofinal))

        adicionar = {'data': datas, 'descricao': descricao, 'valor': valor}
        adicionar = pd.DataFrame(adicionar)

        tabela = pd.concat([tabela, adicionar], ignore_index=True)
        tabela = tabela.sort_values(by=['data'])
        tabela['entradas'] = tabela.apply(
            lambda row: row['valor'] if row['valor'] > 0 and 'SALDO' not in row['descricao'] else '', axis=1)
        tabela['saídas'] = tabela.apply(
            lambda row: row['valor'] if row['valor'] < 0 and 'SALDO' not in row['descricao'] else '', axis=1)
        tabela['saldo'] = tabela.apply(
            lambda row: row['valor'] if 'SALDO' in row['descricao'] else '', axis=1)
        tabela = tabela[['data', 'descricao', 'entradas', 'saídas', 'saldo']]

        if tabela.empty:
            return 'Selecione o mês para filtrar'

        template_html = """
        <table>
            <thead>
                <tr>
                    <th class="w-2/12">Data</th>
                    <th class="w-7/12 text-left">Descrição</th>
                    <th class="w-1/12">Entradas</th>
                    <th class="w-1/12">Saídas</th>
                    <th class="w-1/12">Saldo</th>
                </tr>
            </thead>
            <tbody>
                {% for row in tabela %}
                <tr>
                    <td class="w-2/12">{{ row['data'].strftime('%d/%m/%Y') }}</td>
                    <td class="w-7/12 text-left">{{ row['descricao'] }}</td>
                    <td class="w-1/12">{{ formatar_valor(row['entradas']) if row['entradas'] != '' else '' }}</td>
                    <td class="w-1/12">{{ formatar_valor(row['saídas']) if row['saídas'] != '' else '' }}</td>
                    <td class="w-1/12">{{ formatar_valor(row['saldo']) if row['saldo'] != '' else ''  }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        """
        template = Template(template_html)
        tabela_html = template.render(tabela=tabela.to_dict(orient='records'), formatar_valor=formatar_valor)

    except Exception as e:
        tabela_html = f'Impossível exibir extrato, tente cadastrar um saldo inicial anterior ao mês de visualização. Erro: {e}'

    return tabela_html


def gerar_grafico(cliente, banco, mes):
    try:
        # Conectar ao banco de dados PostgreSQL
        db_url = "postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
        engine = create_engine(db_url)

        # Ler tabelas do banco de dados
        with engine.connect() as conexao:
            tabela = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)
            tabela0 = pd.read_sql("SELECT * FROM financeiro_saldo", conexao)

        # Filtrar e preparar a tabela
        tabela = tabela[(tabela['cliente_id'] == cliente.id) & (tabela['banco_id'] == banco)]
        tabela['data'] = pd.to_datetime(tabela['data'], format='ISO8601')
        tabela['mes'] = tabela['data'].dt.month
        tabela = tabela[tabela['mes'] == mes]
        tabela = tabela[['data', 'descricao', 'valor']].sort_values('data')

        datastabela = tabela[['data']].drop_duplicates()['data']

        if datastabela.empty:
            return 'Selecione o mês para filtrar'

        # Preparar tabela0
        tabela0['data'] = pd.to_datetime(tabela0['data'], format='ISO8601')
        tabela0['mes'] = tabela0['data'].dt.month
        tabela0['ano'] = tabela0['data'].dt.year
        tabela0 = tabela0.sort_values('data')

        ano = datastabela.iloc[0].year
        if mes == 1:
            mes = 12
            ano -= 1
        else:
            mes -= 1

        saldoinicial = tabela0[(tabela0['ano'] == ano) & (tabela0['mes'] == mes) & (tabela0['banco_id'] == banco) &
                               (tabela0['cliente_id'] == cliente.id)]

        if saldoinicial.empty:
            datas = []
            descricao = []
            valor = []
        else:
            saldoinicialdata = saldoinicial['data'].iloc[-1]
            saldoinicialvalor = saldoinicial['saldofinal'].iloc[-1]
            datas = [saldoinicialdata]
            descricao = ['SALDO INICIAL']
            valor = [saldoinicialvalor]

        for data in datastabela:
            descricao.append('SALDO')
            datas.append(data)
            tabela0_filtered = tabela0[(tabela0['cliente_id'] == cliente.id) & (tabela0['banco_id'] == banco)]
            tabela0_filtered = tabela0_filtered.sort_values('data').set_index('data')
            saldofinal = tabela0_filtered.at[data, 'saldofinal']
            valor.append(float(saldofinal))

        adicionar = {'data': datas, 'descricao': descricao, 'valor': valor}
        adicionar = pd.DataFrame(adicionar)

        tabela = pd.concat([tabela, adicionar], ignore_index=True)
        tabela = tabela.sort_values(by=['data'])
        tabela['entradas'] = tabela.apply(
            lambda row: row['valor'] if row['valor'] > 0 and 'SALDO' not in row['descricao'] else '', axis=1)
        tabela['saídas'] = tabela.apply(
            lambda row: row['valor'] if row['valor'] < 0 and 'SALDO' not in row['descricao'] else '', axis=1)
        tabela['saldo'] = tabela.apply(
            lambda row: row['valor'] if 'SALDO' in row['descricao'] else '', axis=1)
        tabela = tabela[['data', 'descricao', 'entradas', 'saídas', 'saldo']]

        if tabela.empty:
            return 'Selecione o mês para filtrar'

        tabela['dia'] = tabela['data'].dt.day

        # Remover linhas com "SALDO INICIAL" na descrição
        tabela = tabela[tabela['descricao'] != 'SALDO INICIAL']

        fig = go.Figure()

        # Adicionar linha de saldo com shape linear
        fig.add_trace(go.Scatter(
            x=tabela['dia'],
            y=tabela['saldo'],
            mode='lines+markers',
            text=tabela['saldo'].apply(lambda x: f'R${float(x):,.2f}' if isinstance(x, (int, float)) else ''),
            line={'dash': 'dashdot'}
        ))

        # Configurar eixos
        fig.update_yaxes(title_text='Saldo', showticklabels=True)
        fig.update_xaxes(title_text='Dia')

        # Remover margens e bordas
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            width=1000,
            height=300
        )

        config = {'displayModeBar': False}
        grafico_html = fig.to_html(full_html=False, config=config)

    except Exception as e:
        grafico_html = f'Impossível exibir gráfico, tente cadastrar um saldo inicial anterior ao mês de visualização. Erro: {e}'

    return grafico_html


def dreresumida(cliente):
    try:
        cliente = cliente  # Atribua a variável cliente corretamente
        mes = datetime.now().month

        # Conectar ao banco de dados PostgreSQL
        db_url = "postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
        engine = create_engine(db_url)

        with engine.connect() as conexao:
            movi = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)
            categoria = pd.read_sql("SELECT * FROM financeiro_categoria", conexao)
            categoriamae = pd.read_sql("SELECT * FROM financeiro_categoriamae", conexao)

        movi['data'] = pd.to_datetime(movi['data'], format='ISO8601')
        movi['mes'] = movi['data'].dt.month
        movi = movi[(movi['cliente_id'] == cliente.id) & (movi['mes'] == mes)]

        categoria = categoria.rename({'id': 'categoria_id', 'nome': 'categoria'}, axis='columns')
        resumo = movi.merge(categoria, on='categoria_id')

        categoriamae = categoriamae.rename({'id': 'categoriamae_id', 'nome': 'categoriamae'}, axis='columns')
        resumo = resumo.merge(categoriamae, on='categoriamae_id')

        resumo = resumo.groupby('categoriamae').sum('valor')
        resumo = resumo[['valor']]

        margem = resumo[:2].sum(numeric_only=True)
        resultado = resumo[:3].sum(numeric_only=True)
        variacao = resumo.sum(numeric_only=True)

        resumo.loc['3.MARGEM DE CONTRIBUIÇÃO'] = pd.Series(margem)
        resumo.loc['5.RESULTADO OPERACIONAL'] = pd.Series(resultado)
        resumo.loc['8.VARIAÇÃO DE CAIXA'] = pd.Series(variacao)

        resumo = resumo.sort_values('categoriamae')
        resumo = resumo.squeeze()

        # Formatação dos valores
        resumo = resumo.apply(lambda x: f"{x:,.2f}")

        return resumo
    
    except:
        resumo = "Sem registros"
        return resumo


def dreprincipal(cliente, ano, centrocusto=None):
    cliente = cliente
    ano = int(ano)

    # Conectar ao banco de dados PostgreSQL
    db_url = "postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
    engine = create_engine(db_url)

    with engine.connect() as conexao:
        movi = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)
        categoria = pd.read_sql("SELECT * FROM financeiro_categoria", conexao)
        categoriamae = pd.read_sql("SELECT * FROM financeiro_categoriamae", conexao)
        subcategoria = pd.read_sql("SELECT * FROM financeiro_subcategoria", conexao)
        centrodecusto = pd.read_sql("SELECT * FROM financeiro_centrodecusto", conexao)

    # Processar as tabelas
    movi['data'] = pd.to_datetime(movi['data'], format='ISO8601')
    movi['mes'] = movi['data'].dt.month
    movi['ano'] = movi['data'].dt.year
    movi = movi[movi['cliente_id'] == cliente.id]

    categoria = categoria[categoria['cliente_id'] == cliente.id]
    categoria = categoria[['id', 'nome', 'categoriamae_id']]
    subcategoria = subcategoria[subcategoria['cliente_id'] == cliente.id]
    subcategoria = subcategoria[['id', 'nome', 'categoria_id']]
    centrodecusto = centrodecusto[centrodecusto['cliente_id'] == cliente.id]
    centrodecusto = centrodecusto[['id', 'nome']]

    categoria = categoria.rename({'id': 'categoria_id', 'nome': 'categoria'}, axis='columns')
    categoriamae = categoriamae.rename({'id': 'categoriamae_id', 'nome': 'categoriamae'}, axis='columns')
    subcategoria = subcategoria.rename({'id': 'subcategoria_id', 'nome': 'subcategoria'}, axis='columns')
    centrodecusto = centrodecusto.rename({'id': 'centrodecusto_id', 'nome': 'centrodecusto'}, axis='columns')

    resumo = movi.merge(categoria, on='categoria_id')
    resumo = resumo.merge(categoriamae, on='categoriamae_id')
    resumo = resumo.merge(subcategoria, on='subcategoria_id')
    resumo = resumo.merge(centrodecusto, on='centrodecusto_id')
    resumo = resumo[['data', 'mes', 'ano', 'categoriamae', 'categoria', 'subcategoria', 'centrodecusto_id', 'valor']]

    # Filtrar os dados para o ano desejado
    ano = ano
    centrocusto = centrocusto

    if centrocusto is None:
        resumo = resumo[resumo['ano'] == ano]
    else:
        centrocusto = float(centrocusto)
        resumo = resumo[(resumo['ano'] == ano) & (resumo['centrodecusto_id'] == centrocusto)]

    # Agrupar os dados
    subcategoria = resumo.groupby(['categoriamae', 'categoria', 'subcategoria', 'mes', 'ano'])[
        'valor'].sum().reset_index()
    categoria = resumo.groupby(['categoriamae', 'categoria', 'mes', 'ano'])['valor'].sum().reset_index()
    categoriamae = resumo.groupby(['categoriamae', 'mes', 'ano'])['valor'].sum().reset_index()

    meses = list(categoriamae['mes'].drop_duplicates().sort_values())

    adccm = []
    adcmes = []
    adcano = []
    adcvalor = []

    for mes in meses:
        margem = categoriamae[
            (categoriamae['categoriamae'] == '1.RECEITAS OPERACIONAIS') & (categoriamae['mes'] == mes) &
            (categoriamae['ano'] == ano) | (categoriamae['categoriamae'] == '2.CUSTOS OPERACIONAIS') &
            (categoriamae['mes'] == mes) & (categoriamae['ano'] == ano)].reset_index()
        if margem.empty:
            margem = 0
        elif margem.size <= 5:
            margem = margem.loc[0, 'valor']
        else:
            margem = margem.loc[0, 'valor'] + margem.loc[1, 'valor']

        resultado = categoriamae[(categoriamae['categoriamae'] == '4.DESPESAS OPERACIONAIS E OUTRAS RECEITAS') &
                                 (categoriamae['mes'] == mes) & (categoriamae['ano'] == ano)].reset_index()

        if resultado.empty:
            resultado = margem + 0
        else:
            resultado = margem + resultado.loc[0, 'valor']

        variacao = categoriamae[(categoriamae['categoriamae'] == '6.ATIVIDADES DE INVESTIMENTO') &
                                (categoriamae['mes'] == mes) & (categoriamae['ano'] == ano) |
                                (categoriamae['categoriamae'] == '7.ATIVIDADES DE FINANCIAMENTO') &
                                (categoriamae['mes'] == mes) & (categoriamae['ano'] == ano)].reset_index()

        if variacao.empty:
            variacao = resultado + 0
        elif variacao.size <= 5:
            variacao = resultado + variacao.loc[0, 'valor']
        else:
            variacao = resultado + variacao.loc[0, 'valor'] + variacao.loc[1, 'valor']

        adccm.append('3.MARGEM DE CONTRIBUIÇÃO')
        adccm.append('5.RESULTADO OPERACIONAL')
        adccm.append('8.VARIAÇÃO DE CAIXA')
        adcmes.append(mes)
        adcmes.append(mes)
        adcmes.append(mes)
        adcano.append(ano)
        adcano.append(ano)
        adcano.append(ano)
        adcvalor.append(margem)
        adcvalor.append(resultado)
        adcvalor.append(variacao)

    adicionar = {'categoriamae': adccm,
                 'mes': adcmes,
                 'ano': adcano,
                 'valor': adcvalor}
    adicionar = pd.DataFrame(adicionar)

    categoriamae = pd.concat([categoriamae, adicionar], ignore_index=True)
    categoriamae = categoriamae.sort_values('categoriamae')

    # Função para criar a tabela final
    def criar_tabela_final(subcategoria, categoria, categoriamae):
        def add_row(level, valores):
            row = {'Nível': level}
            row.update(valores)
            return pd.DataFrame(row, index=[0])

        tabela_final = []

        for cm in categoriamae['categoriamae'].unique():
            cm_valores = categoriamae[categoriamae['categoriamae'] == cm].pivot(index='categoriamae', columns='mes',
                                                                                values='valor').to_dict('index')[cm]
            tabela_final.append(add_row(cm, cm_valores))

            for cat in categoria[categoria['categoriamae'] == cm]['categoria'].unique():
                cat_valores = \
                    categoria[(categoria['categoriamae'] == cm) & (categoria['categoria'] == cat)].pivot(
                        index='categoria',
                        columns='mes',
                        values='valor').to_dict(
                        'index')[cat]
                tabela_final.append(add_row(cat, cat_valores))

                for subcat in subcategoria[(subcategoria['categoriamae'] == cm) &
                                           (subcategoria['categoria'] == cat)]['subcategoria'].unique():
                    subcat_valores = subcategoria[
                        (subcategoria['categoriamae'] == cm) & (subcategoria['categoria'] == cat) & (
                                subcategoria['subcategoria'] == subcat)].pivot(index='subcategoria', columns='mes',
                                                                               values='valor').to_dict('index')[subcat]
                    tabela_final.append(add_row(subcat, subcat_valores))

        # Concatenar todas as linhas em um único DataFrame
        tabela_final = pd.concat(tabela_final, ignore_index=True)

        # Adicionar colunas para todos os meses do ano se não existirem
        for mes in range(1, 13):
            if mes not in tabela_final.columns:
                tabela_final[mes] = 0.0

        # Ordenar as colunas para garantir que os meses estejam na ordem correta
        tabela_final = tabela_final[['Nível'] + list(range(1, 13))]

        # Substituir NaN por 0.0
        tabela_final = tabela_final.fillna(0.0)

        for col in range(1, 13):
            tabela_final[col] = tabela_final[col].apply(lambda x: f"{x:,.2f}")

        # Template HTML para exibir a tabela
        template_html = """
        <table class="drecompleta" border="1">
            <thead>
                <tr>
                    <th class="drecompleta-cabeçalho">Categorias</th>
                    {% for mes in range(1, 13) %}
                        <th class="drecompleta-cabeçalho">{{ mes }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for index, row in tabela_final.iterrows() %}
                    <tr>
                        <td class="drecompleta-categorias">{{ row['Nível'] }}</td>
                        {% for mes in range(1, 13) %}
                            <td class="drecompleta-mes">{{ row[mes] }}</td>
                        {% endfor %}
                    </tr>
                {% endfor %}
            </tbody>
        </table>
        """

        # Renderizar o template com os dados da tabela
        template = Template(template_html)
        html_output = template.render(tabela_final=tabela_final)

        # Exibir o HTML gerado
        return html_output

    tabela_final = criar_tabela_final(subcategoria, categoria, categoriamae)

    return tabela_final


def drecomp(mes1, ano1, mes2, ano2, cliente, centrocusto=None):

    # Conectar ao banco de dados PostgreSQL
    db_url = "postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
    engine = create_engine(db_url)

    with engine.connect() as conexao:
        movi = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)
        categoria = pd.read_sql("SELECT * FROM financeiro_categoria", conexao)
        categoriamae = pd.read_sql("SELECT * FROM financeiro_categoriamae", conexao)
        subcategoria = pd.read_sql("SELECT * FROM financeiro_subcategoria", conexao)
        centrodecusto = pd.read_sql("SELECT * FROM financeiro_centrodecusto", conexao)

    # Processar as tabelas
    movi['data'] = pd.to_datetime(movi['data'], format='ISO8601')
    movi['mes'] = movi['data'].dt.month
    movi['ano'] = movi['data'].dt.year
    movi = movi[movi['cliente_id'] == cliente.id]

    categoria = categoria[categoria['cliente_id'] == cliente.id]
    categoria = categoria[['id', 'nome', 'categoriamae_id']]
    subcategoria = subcategoria[subcategoria['cliente_id'] == cliente.id]
    subcategoria = subcategoria[['id', 'nome', 'categoria_id']]
    centrodecusto = centrodecusto[centrodecusto['cliente_id'] == cliente.id]
    centrodecusto = centrodecusto[['id', 'nome']]

    categoria = categoria.rename({'id': 'categoria_id', 'nome': 'categoria'}, axis='columns')
    categoriamae = categoriamae.rename({'id': 'categoriamae_id', 'nome': 'categoriamae'}, axis='columns')
    subcategoria = subcategoria.rename({'id': 'subcategoria_id', 'nome': 'subcategoria'}, axis='columns')
    centrodecusto = centrodecusto.rename({'id': 'centrodecusto_id', 'nome': 'centrodecusto'}, axis='columns')

    resumo = movi.merge(categoria, on='categoria_id')
    resumo = resumo.merge(categoriamae, on='categoriamae_id')
    resumo = resumo.merge(subcategoria, on='subcategoria_id')
    resumo = resumo.merge(centrodecusto, on='centrodecusto_id')
    resumo = resumo[['data', 'mes', 'ano', 'categoriamae', 'categoria', 'subcategoria', 'centrodecusto_id', 'valor']]

    mes1 = int(mes1)
    ano1 = int(ano1)
    mes2 = int(mes2)
    ano2 = int(ano2)
    centrocusto = centrocusto

    if centrocusto is None:
        resumo = resumo[
            ((resumo['mes'] == mes1) & (resumo['ano'] == ano1)) | ((resumo['mes'] == mes2) & (resumo['ano'] == ano2))]
    else:
        centrocusto = float(centrocusto)
        resumo = resumo[
            ((resumo['mes'] == mes1) & (resumo['ano'] == ano1) & (resumo['centrodecusto_id'] == centrocusto)) |
            ((resumo['mes'] == mes2) & (resumo['ano'] == ano2) & (resumo['centrodecusto_id'] == centrocusto))]

    subcategoria = resumo.groupby(['categoriamae', 'categoria', 'subcategoria', 'mes', 'ano'])['valor'].sum(
        numeric_only=True).reset_index()

    categoria = resumo.groupby(['categoriamae', 'categoria', 'mes', 'ano'])['valor'].sum(
        numeric_only=True).reset_index()

    categoriamae = resumo.groupby(['categoriamae', 'mes', 'ano'])['valor'].sum(numeric_only=True).reset_index()
    
    # Adcionando os calculos de margem, resultado e variação de caixa.
    margem1 = categoriamae[(categoriamae['categoriamae'] == '1.RECEITAS OPERACIONAIS') & (categoriamae['mes'] == mes1) &
                           (categoriamae['ano'] == ano1) | (categoriamae['categoriamae'] == '2.CUSTOS OPERACIONAIS') &
                           (categoriamae['mes'] == mes1) & (categoriamae['ano'] == ano1)].reset_index()

    if margem1.empty:
        margem1 = 0
    elif margem1.size <= 5:
        margem1 = margem1.loc[0, 'valor']
    else:
        margem1 = margem1.loc[0, 'valor'] + margem1.loc[1, 'valor']

    margem2 = categoriamae[(categoriamae['categoriamae'] == '1.RECEITAS OPERACIONAIS') & (categoriamae['mes'] == mes2) &
                           (categoriamae['ano'] == ano2) | (categoriamae['categoriamae'] == '2.CUSTOS OPERACIONAIS') &
                           (categoriamae['mes'] == mes2) & (categoriamae['ano'] == ano2)].reset_index()
    if margem2.empty:
        margem2 = 0
    elif margem2.size <= 5:
        margem2 = 0
    else:
        margem2 = margem2.loc[0, 'valor'] + margem2.loc[1, 'valor']

    resultado1 = categoriamae[(categoriamae['categoriamae'] == '4.DESPESAS OPERACIONAIS E OUTRAS RECEITAS') &
                              (categoriamae['mes'] == mes1) & (categoriamae['ano'] == ano1)].reset_index()

    if resultado1.empty:
        resultado1 = margem1 + 0
    else:
        resultado1 = margem1 + resultado1.loc[0, 'valor']

    resultado2 = categoriamae[(categoriamae['categoriamae'] == '4.DESPESAS OPERACIONAIS E OUTRAS RECEITAS') &
                              (categoriamae['mes'] == mes2) & (categoriamae['ano'] == ano2)].reset_index()

    if resultado2.empty:
        resultado2 = margem2 + 0
    else:
        resultado2 = margem2 + resultado2.loc[0, 'valor']

    variacao1 = categoriamae[(categoriamae['categoriamae'] == '6.ATIVIDADES DE INVESTIMENTO') &
                             (categoriamae['mes'] == mes1) & (categoriamae['ano'] == ano1) |
                             (categoriamae['categoriamae'] == '7.ATIVIDADES DE FINANCIAMENTO') &
                             (categoriamae['mes'] == mes1) & (categoriamae['ano'] == ano1)].reset_index()

    if variacao1.empty:
        variacao1 = resultado1 + 0
    elif variacao1.size <= 5:
        variacao1 = resultado1 + variacao1.loc[0, 'valor']
    else:
        variacao1 = resultado1 + variacao1.loc[0, 'valor'] + variacao1.loc[1, 'valor']

    variacao2 = categoriamae[(categoriamae['categoriamae'] == '6.ATIVIDADES DE INVESTIMENTO') &
                             (categoriamae['mes'] == mes2) & (categoriamae['ano'] == ano2) |
                             (categoriamae['categoriamae'] == '7.ATIVIDADES DE FINANCIAMENTO') &
                             (categoriamae['mes'] == mes2) & (categoriamae['ano'] == ano2)].reset_index()

    if variacao2.empty:
        variacao2 = resultado2 + 0
    elif variacao2.size <= 5:
        variacao2 = resultado2 + variacao2.loc[0, 'valor']
    else:
        variacao2 = resultado2 + variacao2.loc[0, 'valor'] + variacao2.loc[1, 'valor']

    adicionar1 = {'categoriamae': ['3.MARGEM DE CONTRIBUIÇÃO', '5.RESULTADO OPERACIONAL', '8.VARIAÇÃO DE CAIXA'],
                  'mes': [mes1, mes1, mes1],
                  'ano': [ano1, ano1, ano1],
                  'valor': [margem1, resultado1, variacao1]}
    adicionar1 = pd.DataFrame(adicionar1)

    adicionar2 = {'categoriamae': ['3.MARGEM DE CONTRIBUIÇÃO', '5.RESULTADO OPERACIONAL', '8.VARIAÇÃO DE CAIXA'],
                  'mes': [mes2, mes2, mes2],
                  'ano': [ano2, ano2, ano2],
                  'valor': [margem2, resultado2, variacao2]}
    adicionar2 = pd.DataFrame(adicionar2)

    categoriamae = pd.concat([categoriamae, adicionar1, adicionar2], ignore_index=True)
    categoriamae = categoriamae.sort_values('categoriamae')

    # Bases para calculo das porcentagens
    baseporc1 = categoriamae[categoriamae['mes'] == mes1].reset_index()
    baseporc1 = float(baseporc1.loc[0, 'valor'])
    baseporc2 = categoriamae[categoriamae['mes'] == mes2].reset_index()
    baseporc2 = float(baseporc2.loc[0, 'valor'])

    def criar_tabela_final(subcategoria, categoria, categoriamae, mes1, ano1, mes2, ano2):
        tabela_final = []

        for cm in categoriamae['categoriamae'].unique():
            cm_valor1 = categoriamae[
                (categoriamae['categoriamae'] == cm) & (categoriamae['mes'] == mes1) & (categoriamae['ano'] == ano1)][
                'valor'].sum()
            cm_valor2 = categoriamae[
                (categoriamae['categoriamae'] == cm) & (categoriamae['mes'] == mes2) & (categoriamae['ano'] == ano2)][
                'valor'].sum()

            tabela_final.append({
                'Categorias': cm,
                'Valor Mes1': f'{cm_valor1:,.2f}',
                'Porc% Mes1': f'{(cm_valor1 / baseporc1):.2%}' if baseporc1 != 0 else '0.00%',
                'Valor Mes2': f'{cm_valor2:,.2f}',
                'Porc% Mes2': f'{(cm_valor2 / baseporc2):.2%}' if baseporc2 != 0 else '0.00%',
                'Variação': f'{cm_valor2 - cm_valor1:,.2f}',
                'Categoria': []
            })

            for cat in categoria[(categoria['categoriamae'] == cm)]['categoria'].unique():
                cat_valor1 = categoria[
                    (categoria['categoriamae'] == cm) & (categoria['categoria'] == cat) & (categoria['mes'] == mes1) & (
                            categoria['ano'] == ano1)]['valor'].sum()
                cat_valor2 = categoria[
                    (categoria['categoriamae'] == cm) & (categoria['categoria'] == cat) & (categoria['mes'] == mes2) & (
                            categoria['ano'] == ano2)]['valor'].sum()
                tabela_final[-1]['Categoria'].append({
                    'Categorias': cat,
                    'Valor Mes1': f'{cat_valor1:,.2f}',
                    'Porc% Mes1': f'{(cat_valor1 / baseporc1):.2%}' if baseporc1 != 0 else '0.00%',
                    'Valor Mes2': f'{cat_valor2:,.2f}',
                    'Porc% Mes2': f'{(cat_valor2 / baseporc2):.2%}' if baseporc2 != 0 else '0.00%',
                    'Variação': f'{cat_valor2 - cat_valor1:,.2f}',
                    'Subcategoria': []
                })

                for subcat in subcategoria[(subcategoria['categoriamae'] == cm) &
                                           (subcategoria['categoria'] == cat)]['subcategoria'].unique():
                    subcat_valor1 = subcategoria[
                        (subcategoria['categoriamae'] == cm) & (subcategoria['categoria'] == cat) & (
                                subcategoria['subcategoria'] == subcat) & (subcategoria['mes'] == mes1) & (
                                subcategoria['ano'] == ano1)]['valor'].sum()
                    subcat_valor2 = subcategoria[
                        (subcategoria['categoriamae'] == cm) & (subcategoria['categoria'] == cat) & (
                                subcategoria['subcategoria'] == subcat) & (subcategoria['mes'] == mes2) & (
                                subcategoria['ano'] == ano2)]['valor'].sum()
                    tabela_final[-1]['Categoria'][-1]['Subcategoria'].append({
                        'Categorias': subcat,
                        'Valor Mes1': f'{subcat_valor1:,.2f}',
                        'Porc% Mes1': f'{(subcat_valor1 / baseporc1):.2%}' if baseporc1 != 0 else '0.00%',
                        'Valor Mes2': f'{subcat_valor2:,.2f}',
                        'Porc% Mes2': f'{(subcat_valor2 / baseporc2):.2%}' if baseporc2 != 0 else '0.00%',
                        'Variação': f'{subcat_valor2 - subcat_valor1:,.2f}'
                    })

        # Template HTML usando Jinja2
        template_str = """
        <head>
            <style>
                table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: small;
                }
                th, td {
                    text-align: center;
                    padding: 8px;
                }
                th {
                    background-color: #f2f2f2;
                }
                .cm{
                    text-align: left;
                    border-bottom: 1px solid #354255;
                    font-weight: bold;
                }
                .cat{
                    border-bottom: 1px solid #354255;
                    font-weight: bold;
                }
                .cabecalho{
                    background-color: #6f30a0;
                    color: white;
                }
            </style>
        </head>
        <body>
    
        <table>
            <tr>
                <th class="cabecalho text-start">Categorias</th>
                <th class="cabecalho">Valor Mes1</th>
                <th class="cabecalho">Porc% Mes1</th>
                <th class="cabecalho">Valor Mes2</th>
                <th class="cabecalho">Porc% Mes2</th>
                <th class="cabecalho">Variação</th>
            </tr>
            {% for cm in tabela_final %}
            <tr>
                <td class="cm">{{ cm['Categorias'] }}</td>
                <td class="cm text-center">{{ cm['Valor Mes1'] }}</td>
                <td class="cm text-center">{{ cm['Porc% Mes1'] }}</td>
                <td class="cm text-center">{{ cm['Valor Mes2'] }}</td>
                <td class="cm text-center">{{ cm['Porc% Mes2'] }}</td>
                <td class="cm text-center">{{ cm['Variação'] }}</td>
            </tr>
            {% for cat in cm['Categoria'] %}
            <tr>
                <td style="padding-left: 20px;" class="cat text-start">{{ cat['Categorias'] }}</td>
                <td class="cat">{{ cat['Valor Mes1'] }}</td>
                <td class="cat">{{ cat['Porc% Mes1'] }}</td>
                <td class="cat">{{ cat['Valor Mes2'] }}</td>
                <td class="cat">{{ cat['Porc% Mes2'] }}</td>
                <td class="cat">{{ cat['Variação'] }}</td>
            </tr>
            {% for subcat in cat['Subcategoria'] %}
            <tr>
                <td style="padding-left: 40px;" class="text-start">{{ subcat['Categorias'] }}</td>
                <td>{{ subcat['Valor Mes1'] }}</td>
                <td>{{ subcat['Porc% Mes1'] }}</td>
                <td>{{ subcat['Valor Mes2'] }}</td>
                <td>{{ subcat['Porc% Mes2'] }}</td>
                <td>{{ subcat['Variação'] }}</td>
            </tr>
            {% endfor %}
            {% endfor %}
            {% endfor %}
        </table>

        </body>
        """

        # Criar o template Jinja2
        template = Template(template_str)

        # Renderizar o template com os dados da tabela final
        html_output = template.render(tabela_final=tabela_final)

        return html_output

    # Criar a tabela final em formato HTML com acordeão
    tabela_final_html = criar_tabela_final(subcategoria, categoria, categoriamae, mes1, ano1, mes2, ano2)

    # Retornar o código HTML resultante
    return tabela_final_html

    