from multiprocessing.reduction import send_handle
from os import getenv

from Demos.win32ts_logoff_disconnected import username
from IPython.lib.editorhooks import emacs
from django.apps import AppConfig


class HpinicialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hpinicial'

    def ready(self):
        from .models import Usuario
        import os

        email = os.getenv("EMAIL_ADMIN")
        senha = os.getenv("SENHA_ADMIN")

        Usuario.objects.create_superuser(username="admin", email=email, password=senha, is_active=True, is_staff=True)