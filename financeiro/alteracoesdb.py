import pandas as pd
import sqlite3
from .models import Saldo, BancosCliente
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import dask.dataframe as dd
from datetime import datetime, timedelta
from django.db import transaction
import psycopg2


def saldodiario(banco, cliente, data):
    datainicial = datetime.strptime(data, '%Y-%m-%d').date()
    datainicialord = datainicial.toordinal() + 1
    datafinal = datainicialord + 31

    for data_ord in range(datainicialord, datafinal):
        data = datetime.fromordinal(data_ord).date()
        data_anterior = datetime.fromordinal(data_ord - 1).date()

        # Conectar ao banco de dados PostgreSQL
        with psycopg2.connect(
                dbname='railway',
                user='postgres',
                password='rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg',
                host='postgres.railway.internal',
                port='5432'
        ) as conexao:
            tabela_saldo = pd.read_sql("SELECT * FROM financeiro_saldo", conexao)
            tabela_mov = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)

        saldoinicial = tabela_saldo[
            (tabela_saldo['cliente_id'] == cliente.id) &
            (tabela_saldo['banco_id'] == banco) &
            (tabela_saldo['data'] == str(data_anterior))
            ]['saldofinal'].sum() if not tabela_saldo.empty else 0

        saldodia = tabela_mov[
            (tabela_mov['cliente_id'] == cliente.id) &
            (tabela_mov['banco_id'] == banco) &
            (tabela_mov['data'] == str(data))
            ]['valor'].sum() if not tabela_mov.empty else 0

        saldofinal = saldoinicial + saldodia

        Saldo.objects.update_or_create(
            data=data,
            banco=BancosCliente.objects.get(id=banco),
            cliente=cliente,
            defaults={
                'saldoinicial': float(saldoinicial),
                'saldofinal': float(saldofinal)
            }
        )



def alteracaosaldo(banco, cliente, data, dias=0):
    # Conversão inicial da data
    datainicial = datetime.strptime(data, '%Y-%m-%d').date()
    datafinal = datainicial + timedelta(days=31 + dias)

    current_date = datainicial
    
    while current_date <= datafinal:
        data_str = current_date.strftime('%Y-%m-%d')
        data_anterior_str = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')

        # Conectar ao banco de dados uma vez
        with psycopg2.connect(
                dbname='railway',
                user='postgres',
                password='rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg',
                host='postgres.railway.internal',
                port='5432'
        ) as conexao:
            # Ler tabelas uma vez
            tabela_saldo = pd.read_sql("SELECT * FROM financeiro_saldo", conexao)
            tabela_movimentacoes = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)

        # Fechar a conexão
        conexao.close()
        
        # Cálculo do saldo inicial
        saldoinicial = tabela_saldo[
            (tabela_saldo['cliente_id'] == cliente.id) & 
            (tabela_saldo['banco_id'] == int(banco)) & 
            (tabela_saldo['data'] == data_anterior_str)
        ]
        saldoinicial = saldoinicial['saldofinal'].sum() if not saldoinicial.empty else 0
        
        # Cálculo do saldo diário
        saldodia = tabela_movimentacoes[
            (tabela_movimentacoes['cliente_id'] == cliente.id) & 
            (tabela_movimentacoes['banco_id'] == int(banco)) & 
            (tabela_movimentacoes['data'] == data_str)
        ]
        saldodia = saldodia['valor'].sum() if not saldodia.empty else 0
        
        saldofinal = saldoinicial + saldodia
        
        # Atualização do banco de dados Django
        with transaction.atomic():
            saldo, criado = Saldo.objects.update_or_create(
                data=data_str,
                banco=BancosCliente.objects.get(id=banco),
                cliente=cliente.id,
                defaults={'saldoinicial': float(saldoinicial), 'saldofinal': float(saldofinal)},
            )
        
        current_date += timedelta(days=1)