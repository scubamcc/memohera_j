
web: python manage.py create_initial_superuser && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn memohera_project.wsgi:application --bind 0.0.0.0:$PORT