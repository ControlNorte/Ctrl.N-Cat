from django.test import TestCase

from financeiro.views import financeiro_view
from .models import Tenant
from cliente.models import cadastro_de_cliente

class TenantFilteringTest(TestCase):
    def setUp(self):
        self.tenant1 = Tenant.objects.create(name='Tenant 1', subdomain='tenant1')
        self.tenant2 = Tenant.objects.create(name='Tenant 2', subdomain='tenant2')
        cadastro_de_cliente.objects.create(tenant=self.tenant1, amount=100, description='Test 1', date='2024-01-01')
        cadastro_de_cliente.objects.create(tenant=self.tenant2, amount=200, description='Test 2', date='2024-01-02')

    def test_tenant_filtering(self):
        request = self.factory.get('/transactions/')
        request.tenant = self.tenant1
        response = financeiro_view(request)
        self.assertEqual(response.context['transactions'].count(), 1)
        self.assertEqual(response.context['transactions'].first().description, 'Test 1')