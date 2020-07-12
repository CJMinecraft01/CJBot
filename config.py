"""
Configuration options for the Flask application
"""

import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.join(BASEDIR, 'database'), 'database.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
DEBUG = False
SECRET_KEY = 'development'
CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 300