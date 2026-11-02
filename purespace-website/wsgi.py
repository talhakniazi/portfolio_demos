"""WSGI entry point for Gunicorn, uWSGI, PythonAnywhere, etc.:  gunicorn wsgi:app"""
from purespace import create_app

app = create_app()
