from django.db import models
from hpinicial.managers import TenantManager
from hpinicial.models import Tenant


LISTA_ESTADOS = (
        ('AC','Acre'),
        ('AL','Alagoas'),
        ('AP','Amapá'),
        ('AM','Amazonas'),
        ('BA','Bahia'),
        ('CE','Ceará'),
        ('ES','Espírito Santo'),
        ('GO','Goiás'),
        ('MA','Maranhão'),
        ('MT','Mato Grosso'),
        ('MS','Mato Grosso do Sul'),
        ('MG','Minas Gerais'),
        ('PA','Pará'),
        ('PB','Paraíba'),
        ('PR','Paraná'),
        ('PE','Pernambuco'),
        ('PI','Piauí'),
        ('RJ','Rio de Janeiro'),
        ('RN','Rio Grande do Norte'),
        ('RS','Rio Grande do Sul'),
        ('RO','Rondônia'),
        ('RR','Roraima'),
        ('SC','Santa Catarina'),
        ('SP','São Paulo'),
        ('SE','Sergipe'),
        ('TO','Tocantins'),
        ('DF','Distrito Federal'),
)

LISTA_RAMOS = (
    ('ALIMENTAÇÃO','Alimentação'),
    ('INDUSTRIA','Indústria'),
    ('COMERCIO','Comércio'),
    ('SAUDE','Saúde'),
    ('SERVICOS','Serviços')
)


class Ramo(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.nome


class cadastro_de_cliente(models.Model):
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    razao_social = models.CharField(max_length=100, null=True, blank=True)
    cnpj = models.CharField(max_length=100, null=True, blank=True)
    logadouro = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    número = models.IntegerField(null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=100, choices=LISTA_ESTADOS, null=True, blank=True)
    pessoa_de_contato = models.CharField(max_length=100, null=True, blank=True)
    telefone = models.CharField(max_length=100, null=True, blank=True)
    email_contato = models.CharField(max_length=100, null=True, blank=True)
    ramo = models.ForeignKey(Ramo, null=True, on_delete=models.SET_NULL)
    ativo = models.BooleanField(default=True)
    bancos_utilizados = models.CharField(max_length=100, null=True, blank=True)
    servicos_contratados = models.CharField(max_length=100, null=True, blank=True)
    responsavel_conciliacao = models.CharField(max_length=100, null=True, blank=True)
    responsavel_apresentacao = models.CharField(max_length=100, null=True, blank=True)
    funcionarios = models.TextField(max_length=500, null=True, blank=True)
    contas_fixas = models.TextField(max_length=500, null=True, blank=True)
    classificacoes = models.TextField(max_length=500, null=True, blank=True)
    principais_fornecedores = models.TextField(max_length=500, null=True, blank=True)
    observacoes = models.TextField(max_length=500, null=True, blank=True)
    sugestoes = models.TextField(max_length=500, null=True, blank=True)
    historico = models.TextField(max_length=500, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    data_inicio_plano = models.DateTimeField(null=True, blank=True, default=None)
    tempo_plano = models.CharField(max_length=100, null=True, blank=True, default=None)
    data_final_plano = models.DateTimeField(null=True, blank=True, default=None)
    tempo_plano1 = models.CharField(max_length=100, null=True, blank=True, default=None)

    objects = TenantManager()

    def __str__(self):
        return self.razao_social
