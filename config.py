"""
Configuration options for the Flask application
"""

import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.join(BASEDIR, 'database'), 'database.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
DEBUG = False
# SECRET_KEY = '\x97\xab_d\xdak\x91\x122m\x81\xd5\x01\xe3\x8c4\xddN$\xd4s\x84\xd9z'
SECRET_KEY = 'development'
CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 300