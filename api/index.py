"""Vercel serverless function entry point."""
import sys
import os

# Add the parent directory to the path so we can import 'app'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

# Vercel requires exporting the app directly as WSGI
__all__ = ['app']
