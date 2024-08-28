from django.utils.deprecation import MiddlewareMixin
from .models import Tenant


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):
        subdomain = request.get_host().split('.')[0]
        try:
            request.tenant = Tenant.objects.get(subdomain=None)
        except Tenant.DoesNotExist:
            request.tenant = None