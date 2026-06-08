import os

# Make sure to set these in your environment or .env file
secret_key = os.environ.get('SECRET_KEY', 'default_random_secret')
salt = os.environ.get('SALT', 'default_random_salt')
