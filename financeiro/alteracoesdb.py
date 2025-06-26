import pandas as pd
import sqlite3

from django.db.models import Sum

from .models import Saldo, BancosCliente, MovimentacoesCliente
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import dask.dataframe as dd
from datetime import datetime, timedelta
from django.db import transaction, connection
import logging


def saldodiario(banco, cliente, data, request):
    datainicial = datetime.strptime(data, '%Y-%m-%d').date()
    datainicialord = datainicial.toordinal() + 1

    datafinal = MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente.id, banco=banco).order_by('-data').first()
    datafinal = datafinal.data + timedelta(days=31) if datafinal else datainicial + timedelta(days=31)
    datafinal = datafinal.toordinal()

    for data_ord in range(datainicialord, datafinal):
        # Configurar a string de conexão com o SQLAlchemy
        db_url = "postgresql://postgres:mdcOQHlvdMKsOBUxIBQJgeuDcugbAhjh@postgres.railway.internal:5432/railway"
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
            tenant=request.tenant,
            data=data,
            banco=BancosCliente.objects.for_tenant(request.tenant).get(id=banco),
            cliente=cliente,
            defaults={
                'saldoinicial': float(saldoinicial),
                'saldofinal': float(saldofinal)
            }
        )


def alteracaosaldo(banco, cliente, data, request):
    datainicial = datetime.strptime(data, "%Y-%m-%d").date()  # Determina a menor data entre as movimentações
    datafinal = MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente, banco=banco).order_by('-data').first()
    datafinal = datafinal.data + timedelta(days=31) if datafinal else datetime.strptime(datainicial,"%Y-%m-%d") + timedelta(days=31)  # Determina a maior data entre as movimentações

    while datainicial <= datafinal:
        # Calcula o saldo inicial e final do dia
        saldo_inicial = Saldo.objects.for_tenant(request.tenant).filter(cliente=cliente, banco=banco,
                                          data=datainicial - timedelta(days=1)).first()

        saldo_inicial = saldo_inicial.saldofinal if saldo_inicial else 0  # Obtém o saldo final do dia anterior

        saldo_movimentacoes = \
            MovimentacoesCliente.objects.for_tenant(request.tenant).filter(cliente=cliente, banco=banco, data=datainicial).aggregate(
                total_movimentacoes=Sum('valor'))['total_movimentacoes'] or 0

        saldo_final = saldo_inicial + saldo_movimentacoes

        tenant = int(request.tenant.id)

        with connection.cursor() as cursor:
            insert_query = """
                        INSERT INTO financeiro_saldo (tenant_id, cliente_id, banco_id, data, saldoinicial, saldofinal)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tenant_id, cliente_id, banco_id, data)
                        DO UPDATE SET saldoinicial = EXCLUDED.saldoinicial, saldofinal = EXCLUDED.saldofinal;
                    """

            cursor.execute(insert_query, [
                tenant,
                cliente,
                banco,
                datainicial,
                saldo_inicial,
                saldo_final
            ])

        datainicial += timedelta(days=1)  # Incrementa o dia

    return print('Saldo Alterado com Sucesso!')

