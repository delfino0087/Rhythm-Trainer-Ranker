import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///rhythm_trainer.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False