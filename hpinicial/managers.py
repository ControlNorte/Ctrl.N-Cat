from django.db import models


class TenantManager(models.Manager):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)