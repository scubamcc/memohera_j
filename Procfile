
web: python manage.py collectstatic --noinput && python manage.py migrate && gunicorn memohera_project.wsgi:application --bind 0.0.0.0:$PORT