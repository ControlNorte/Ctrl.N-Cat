import pandas as pd
import sqlite3
from .models import Saldo, BancosCliente, MovimentacoesCliente
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import dask.dataframe as dd
from datetime import datetime, timedelta
from django.db import transaction
import psycopg2
import logging


def saldodiario(banco, cliente, data):
    datainicial = datetime.strptime(data, '%Y-%m-%d').date()
    datainicialord = datainicial.toordinal() + 1

    datafinal = MovimentacoesCliente.objects.filter(cliente=cliente.id, banco=banco).order_by('-data').first()
    datafinal = datafinal.data + timedelta(days=31) if datafinal else datetime.strptime(datainicial, "%Y-%m-%d") + timedelta(days=31)
    datafinal = datafinal.toordinal()

    for data_ord in range(datainicialord, datafinal):
        # Configurar a string de conexão com o SQLAlchemy
        db_url = "postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
        engine = create_engine(db_url)

        with engine.connect() as conexao:
            tabela_saldo = pd.read_sql("SELECT * FROM financeiro_saldo", conexao)
            tabela_mov = pd.read_sql("SELECT * FROM financeiro_movimentacoescliente", conexao)

        conexao.close()

        data = datetime.fromordinal(data_ord).date()
        data_anterior = datetime.fromordinal(data_ord - 1).date()

        saldoinicial = tabela_saldo[
            (tabela_saldo['cliente_id'] == cliente.id) &
            (tabela_saldo['banco_id'] == banco) &
            (tabela_saldo['data'] == data_anterior)
            ]['saldofinal'].sum()

        saldodia = tabela_mov[
            (tabela_mov['cliente_id'] == cliente.id) &
            (tabela_mov['banco_id'] == banco) &
            (tabela_mov['data'] == data)
            ]['valor'].sum()

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


logger = logging.getLogger(__name__)

def alteracaosaldo(banco, cliente, data, dias=0):
    try:
        logger.info(f"Iniciando alteracaosaldo para banco {banco}, cliente {cliente.id}, data {data}")

        # Conversão inicial da data
        datainicial = datetime.strptime(data, '%Y-%m-%d').date()
        datafinal = datainicial + timedelta(days=31 + dias)

        db_url = r"postgresql://postgres:rJAVyBfPxCTZWlHqnAOTZpmwABaKyaWg@postgres.railway.internal:5432/railway"
        engine = create_engine(db_url)

        with engine.connect() as conexao:
            # Filtrar as tabelas diretamente na consulta SQL
            query_saldo = f"""
            SELECT * FROM financeiro_saldo 
            WHERE cliente_id = {cliente.id} 
            AND banco_id = {int(banco)} 
            AND data BETWEEN '{datainicial}' AND '{datafinal}'
            """
            logger.info(f"Executando query de saldo: {query_saldo}")
            tabela_saldo = pd.read_sql(query_saldo, conexao)

            query_movimentacoes = f"""
            SELECT * FROM financeiro_movimentacoescliente 
            WHERE cliente_id = {cliente.id} 
            AND banco_id = {int(banco)} 
            AND data BETWEEN '{datainicial}' AND '{datafinal}'
            """
            logger.info(f"Executando query de movimentações: {query_movimentacoes}")
            tabela_movimentacoes = pd.read_sql(query_movimentacoes, conexao)

            current_date = datainicial
            while current_date <= datafinal:
                data_str = current_date.strftime('%Y-%m-%d')
                data_anterior_str = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')

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

                # Log do saldo calculado
                logger.info(f"Data: {data_str}, Saldo Inicial: {saldoinicial}, Saldo do Dia: {saldodia}, Saldo Final: {saldofinal}")

                # Atualização do banco de dados Django
                with transaction.atomic():
                    saldo, criado = Saldo.objects.update_or_create(
                        data=data_str,
                        banco=BancosCliente.objects.get(id=banco),
                        cliente=cliente,
                        defaults={'saldoinicial': float(saldoinicial), 'saldofinal': float(saldofinal)},
                    )
                    logger.info(f"Saldo {'criado' if criado else 'atualizado'} no banco de dados para data {data_str}")

                current_date += timedelta(days=1)

        logger.info(f"Finalização de alteracaosaldo para banco {banco}, cliente {cliente.id}, data {data}")

    except Exception as e:
        logger.error(f"Erro ao executar alteracaosaldo para banco {banco}, cliente {cliente.id}, data {data}: {e}")
        raise
