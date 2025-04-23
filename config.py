import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    AUTHORITY = os.getenv('AUTHORITY')
    AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
    AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
    SHAREPOINT_SITE_ID = os.getenv('SHAREPOINT_SITE_ID')
    SETUP_SECRET = os.getenv('SETUP_SECRET')
    PORT = os.getenv('PORT')
    MS_APP_ID = os.getenv('MS_APP_ID')
    MS_APP_PASSWORD = os.getenv('MS_APP_PASSWORD')