from django.utils.deprecation import MiddlewareMixin
from .models import Tenant


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):
        tenant = request.user.tenant
        try:
            request.tenant = Tenant.objects.get(id=tenant)
            print(request.tenant)
        except Tenant.DoesNotExist:
            request.tenant = None
            print(None)