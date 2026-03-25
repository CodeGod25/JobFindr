"""
Vercel serverless entry point for JobFindr.
Vercel calls this file and expects an 'app' (WSGI) object.
"""
import sys
import os

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app

app = create_app()
