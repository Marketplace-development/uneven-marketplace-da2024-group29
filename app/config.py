class Config: 
    SECRET_KEY = 'your_secret_key'
    
    SQLALCHEMY_DATABASE_URI = (
        'postgresql://postgres.rniucvwgcukfmgiscgzj:DBS2024_Ugent@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require'
    ) # weet niet of '?sslmode=required' er nog na moet want dit staat ook niet in de link
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    
