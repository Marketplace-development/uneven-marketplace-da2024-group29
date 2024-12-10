import os #nodig om flash berichten te laten verschijnen


class Config: 
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here'  #eerste gedeelte nodig om Flash berichten te laten verschijnen
    
    SQLALCHEMY_DATABASE_URI = (
        'postgresql://postgres.rniucvwgcukfmgiscgzj:DBS2024_Ugent@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require&gssencmode=disable'
    ) # weet niet of '?sslmode=required' er nog na moet want dit staat ook niet in de link
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

GOOGLE_MAPS_API_KEY = "AIzaSyDZoTidAslIv8u7dHvcY9_AdLaE5f8Nikw"




    
