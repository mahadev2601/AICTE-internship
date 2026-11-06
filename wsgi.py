"""
wsgi.py — WSGI entry point for production servers (Gunicorn, uWSGI).
Render, Railway, Heroku and similar platforms import 'app' from here.
"""
from app import app

if __name__ == "__main__":
    app.run()
