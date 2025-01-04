from django.apps import AppConfig


class HpinicialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hpinicial'

    def ready(self):
        from .models import Usuario
        import os

        email = os.getenv("EMAIL_ADMIN")
        senha = os.getenv("SENHA_ADMIN")

        usuarios = Usuario.objects.filter(email=email)
        if not usuarios:
            usuarios.objects.creat_superuser(username="admin", email=email, password=senha, is_active=True, is_staff=True)