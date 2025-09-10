import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'mysql+pymysql://user:password@localhost/shift_handover')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Flask-Mail config for Gmail SMTP
    MAIL_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('SMTP_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('SMTP_USERNAME', 'mdsajid020@gmail.com')
    MAIL_PASSWORD = os.getenv('SMTP_PASSWORD', 'uovrivxvitovrjcu')
    MAIL_DEFAULT_SENDER = os.getenv('TEAM_EMAIL', 'mdsajid020@gmail.com')
    TEAM_EMAIL = os.getenv('TEAM_EMAIL', 'mdsajid020@gmail.com')
