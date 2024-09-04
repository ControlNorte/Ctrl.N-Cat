from django.utils.deprecation import MiddlewareMixin
from .models import Tenant


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):
        try:
            tenant = request.user.tenant
            request.tenant = Tenant.objects.get(id=tenant.id)
        except Tenant.DoesNotExist:
            request.tenant = None