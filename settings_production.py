from .settings import *
import os

# Production settings
DEBUG = False
ALLOWED_HOSTS = ['.railway.app', 'your-domain.com']  # Railway will auto-populate

# Database for production (Railway will provide this)
import dj_database_url
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
}

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Add to your installed apps
INSTALLED_APPS += ['whitenoise.runserver_nostatic']

# Add to middleware (at the top)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')