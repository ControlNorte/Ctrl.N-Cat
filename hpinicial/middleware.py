from django.utils.deprecation import MiddlewareMixin
from .models import Tenant


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):
        subdomain = request.get_host().split('.')[0]
        print(subdomain)
        try:
            request.tenant = Tenant.objects.get(subdomain=subdomain)
            print(request.tenant)
        except Tenant.DoesNotExist:
            request.tenant = None
            print(None)