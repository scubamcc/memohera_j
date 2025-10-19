from django.apps import AppConfig

class MemorialsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'memorials'

class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'your_app_name'
    
    def ready(self):
        import your_app_name.signals  # Import signals when app is ready