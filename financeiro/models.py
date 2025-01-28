from django.db import models
from cliente.models import cadastro_de_cliente
from hpinicial.models import Tenant
from hpinicial.managers import TenantManager
# Create your models here.


class BancosCliente(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    banco = models.CharField(max_length=100)
    agencia = models.IntegerField()
    conta = models.IntegerField()
    digito = models.IntegerField()
    ativo = models.BooleanField(null=True, blank=True)
    accountId = models.CharField(null=True, blank=True, default=None, unique=True)

    objects = TenantManager()

    def __str__(self):
        return f"{self.banco}, Cliente: {self.cliente} Ativo: {self.ativo}"


class CategoriaMae(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.nome


class Categoria(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    categoriamae = models.ForeignKey(CategoriaMae, null=True, on_delete=models.SET_NULL)
    nome = models.CharField(max_length=100)

    objects = TenantManager()

    def __str__(self):
        return self.nome


class SubCategoria(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, null=True, on_delete=models.SET_NULL)
    nome = models.CharField(max_length=100)

    objects = TenantManager()

    def __str__(self):
        return self.nome


class CentroDeCusto(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(null=True, blank=True)

    objects = TenantManager()

    def __str__(self):
        return self.nome


class MovimentacoesCliente(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, null=True, on_delete=models.SET_NULL)
    subcategoria = models.ForeignKey(SubCategoria, null=True, on_delete=models.SET_NULL)
    centrodecusto = models.ForeignKey(CentroDeCusto, null=True, on_delete=models.SET_NULL)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    banco = models.ForeignKey(BancosCliente, null=True, on_delete=models.SET_NULL)
    data = models.DateField()
    descricao = models.CharField(max_length=100, blank='Sem Descrição')
    detalhe = models.CharField(max_length=100, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    objects = TenantManager()


class TransicaoCliente(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    banco = models.ForeignKey(BancosCliente, null=True, on_delete=models.SET_NULL)
    data = models.DateField()
    descricao = models.CharField(max_length=100, blank='Sem Descrição')
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    objects = TenantManager()


class Regra(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, null=True, on_delete=models.SET_NULL)
    subcategoria = models.ForeignKey(SubCategoria, null=True, on_delete=models.SET_NULL)
    centrodecusto = models.ForeignKey(CentroDeCusto, null=True, on_delete=models.SET_NULL)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    descricao = models.CharField(max_length=100, blank='Sem Descrição')
    ativo = models.BooleanField(null=True, blank=True)

    objects = TenantManager()


class Saldo(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    banco = models.ForeignKey(BancosCliente, null=True, on_delete=models.CASCADE)
    cliente = models.ForeignKey(cadastro_de_cliente, on_delete=models.CASCADE)
    data = models.DateField()
    saldoinicial = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    saldofinal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    objects = TenantManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['banco', 'cliente', 'data'], name='unique_banco_cliente_data')
        ]

    def __str__(self):
        return f'{self.cliente}, {self.banco.banco}'


class UploadedFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)