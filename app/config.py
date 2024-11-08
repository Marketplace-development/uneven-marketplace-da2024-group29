class Config: 
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres.username:password@localhost:port/dbname'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    