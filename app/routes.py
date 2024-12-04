from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from .models import db, User, Vendor, Customer, Meal_offerings, Review, CuisineType, MealStatus, Transaction, TransactionStatus
import os  # For working with file paths
import datetime
from supabase import create_client, Client  # For connecting to Supabase
from datetime import datetime
import re

SUPABASE_URL = "https://rniucvwgcukfmgiscgzj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJuaXVjdndnY3VrZm1naXNjZ3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzA4OTcyNDQsImV4cCI6MjA0NjQ3MzI0NH0.8ukVk16UcFWMS6r6cfDGefE2hTkQGia8v53luWNRBRc"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


main = Blueprint('main', __name__)

@main.route('/register', methods=['GET', 'POST'])
def register():
    print(f"Session user_id: {session.get('user_id')}")  # Toont de opgeslagen session user_id

    if request.method == 'POST':
        #Haal gegevens uit het formulier
        username = request.form['username'].strip() 
        email = request.form['email'].strip()
        street = request.form['street'].strip()
        number = request.form['number'].strip()
        zip = request.form['zip'].strip()
        city = request.form['city'].strip()

        # Validatie van verplichte velden
        if not username or not email or not street or not number or not zip or not city:
            flash("All fields are required!")
            return redirect(url_for('main.register'))

         # Controleer of de gebruiker al bestaat
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("User already exists. Please choose a different username or log in.")
            return redirect(url_for('main.register'))
        
        # Als de gebruiker niet bestaat, voeg toe aan de database
        new_user = User(
            username=username,
            email=email,
            street=street,
            number=number,
            zip=zip,
            city=city,
            type='user'  # Standaardwaarde
        )  

        db.session.add(new_user)
        db.session.commit()  # Sla de gebruiker op in de database

        # Zet de gebruiker in de sessie (om automatisch ingelogd te zijn)
        session['user_id'] = new_user.user_id
        vendor_id = new_user.user_id
        customer_id = new_user.user_id
        flash("User registered successfully!")

        # Redirect naar de indexpagina (na succesvolle registratie)
        return redirect(url_for('main.index'))
        
    return render_template('2. Signup.html')  # Render de registratiepagina (GET-request)


# Login route: gebruikers kunnen zich hier aanmelden met hun gebruikersnaam
@main.route('/login', methods=['GET', 'POST'])
def login():
    print(f"Session user_id: {session.get('user_id')}")  # Toont de opgeslagen session user_id

    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()  # Zoek de gebruiker in de database
        if user:
            session['user_id'] = user.user_id  # Zet de gebruiker in de sessie
            return redirect(url_for('main.index'))  # Redirect naar de indexpagina
        flash("User not found, please try again.")  # Toon een foutmelding als de gebruiker niet bestaat
    return render_template('1.Login.html')  # Toon de loginpagina

# Logout route: gebruiker kan uitloggen
@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Verwijder de gebruiker uit de sessie
    return redirect(url_for('main.login'))  # Na uitloggen, stuur naar de loginpagina


@main.route('/base')
def base():
    return render_template('base.html')

def upload_to_supabase_storage(bucket_name, file, filename):
    response = supabase.storage.from_(bucket_name).upload(filename, file)
    if response.get("error"):
        print("Error uploading file:", response["error"])
        return None
    return supabase.storage.from_(bucket_name).get_public_url(filename)

@main.route('/add-meal', methods=['GET', 'POST'])
def add_meal():
    user_id = session.get('user_id')
    if request.method == 'POST':
        # Retrieve meal details from the form
        name = request.form['name']
        description = request.form['description']
        picture = request.files.get('picture')
        cuisine = request.form['cuisine']

        # Validation: Ensure both name and cuisine are provided
        if not name or not cuisine:
            flash("Meal name and cuisine type are required!", "error")
            return redirect(url_for('main.add_meal'))
        
        if not user_id:
            flash("You must be logged in to add a meal.", "error")
            return redirect(url_for('main.login'))

        picture_url = None
        if picture:
            def sanitize_filename(filename):
                cleaned_filename = re.sub(r'[^\w\-_\.]', '_', filename)
                return cleaned_filename
            
            original_filename = picture.filename
            sanitized_filename = sanitize_filename(original_filename)

            filename = f"{user_id}_{datetime.utcnow().isoformat()}_{sanitized_filename}"
            
            response = supabase.storage.from_('picture').upload(filename, picture.read())
            if not response:
                flash("Error uploading image to Supabase.", "error")
                return redirect(url_for('main.add_meal'))
            picture_url = supabase.storage.from_('picture').get_public_url(filename)
        
        # Controleer of user_id al bestaat in Vendors.vendor_id
        existing_vendor = Vendor.query.filter_by(vendor_id=user_id).first()

        if not existing_vendor:
            # Als de gebruiker nog geen vendor is, voeg toe
            vendor = Vendor(vendor_id=user_id)
            db.session.add(vendor)
            db.session.commit()

        # Create the new meal record in the database
        new_meal = Meal_offerings(
            name=name,
            description=description,
            picture=picture_url,  # Store the URL or file path to the uploaded image
            vendor_id=user_id,
            cuisine=CuisineType[cuisine] 
        )

        # Commit the meal record to the database
        db.session.add(new_meal)
        db.session.commit()

        

        # Flash a success message and redirect to the index page
        flash("Meal added successfully!", "success")
        return redirect(url_for('main.index'))

    # Render the meal creation page if it's a GET request
    return render_template('4.Meal_Creation.html', cuisines=CuisineType)


#Functie om maaltijd te kopen -> snel gekopieerd en geplakt van chatgpt, nog niet deftig bekeken
@main.route('/buy-meal/<int:meal_id>', methods=['POST'])
def buy_meal(meal_id):
    # Haal de ingelogde gebruiker op
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        flash("You must be logged in to buy a meal.")
        return redirect(url_for('main.login'))

    # Haal de maaltijd op
    meal = Meal_offerings.query.get(meal_id)
    if not meal:
        flash("Meal not found.")
        return redirect(url_for('main.index'))

    # Controleer of de gebruiker de maaltijd niet zelf heeft toegevoegd
    if meal.vendor_id == user.user_id:
        flash("You cannot buy your own meal!")
        return redirect(url_for('main.index'))

    # Maak een nieuwe transactie
    new_transaction = Transaction(
        status=TransactionStatus.CONCEPT,
        meal_id=meal_id,
        customer_id=user.user_id,
        vendor_id=meal.vendor_id
    )

    db.session.add(new_transaction)
    db.session.commit()
    flash("Transaction started successfully!")
    return redirect(url_for('main.index'))



# Begin van algoritme filteren op keuken/stad/beoordeling
@main.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op
        city = user.city  # Haal de stad van de ingelogde gebruiker op
        cuisine_filter = request.args.get('cuisine', None)  # Haal het cuisine filter op
        
        # Haal alle maaltijden (MealOffering) op en filteren op cuisine
        meal_offerings = Meal_offerings.query.all()
        if cuisine_filter:
            meal_offerings = [meal for meal in meal_offerings if Meal_offerings.cuisine == CuisineType[cuisine_filter]]

        # Filteren op stad
        local_meals = [meal for meal in meal_offerings if User.city == city]  # Lokale maaltijden
        other_meals = [meal for meal in meal_offerings if User.city != city]  # Andere maaltijden
        meal_offerings_sorted = local_meals + other_meals  # Lokale maaltijden bovenaan

        # Bereken de gemiddelde beoordeling voor maaltijden
        # def get_average_rating(meal_id):
            # reviews = Review.query.filter_by(meal_id=meal_id).all()
            # if reviews:
                # total_score = sum(review.score for review in reviews)
                # return total_score / len(reviews)
            # return 0

        # Sorteer maaltijden op basis van beoordeling
        # meal_offerings_sorted = sorted(meal_offerings_sorted, key=lambda Meal_offerings: get_average_rating(Meal_offerings.meal_id), reverse=True)

        return render_template('index.html', username=User.username, listings=meal_offerings_sorted)
    else:
        return redirect(url_for('main.login'))  # Als de gebruiker niet is ingelogd, stuur naar loginpagina

#mealdetails
@main.route('/claim-meal/<int:meal_id>', methods=['POST'])
def claim_meal(meal_id):
    # Fetch the logged-in user
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to claim a meal.", "error")
        return redirect(url_for('main.login'))

    # Fetch the meal
    meal = Meal_offerings.query.get_or_404(meal_id)
    
    # Ensure the user is not claiming their own meal
    if meal.vendor_id == user_id:
        flash("You cannot claim your own meal!", "error")
        return redirect(url_for('main.index'))

    # Update the meal or transaction status as needed
    transaction = Transaction(
        status=TransactionStatus.COMPLETED,
        meal_id=meal_id,
        customer_id=user_id,
        vendor_id=meal.vendor_id
    )
    db.session.add(transaction)
    db.session.commit()

    flash("Meal successfully claimed!", "success")
    return redirect(url_for('main.pick_up', meal_id=meal_id))

@main.route('/pick-up/<int:meal_id>', methods=['GET'])
def pick_up(meal_id):
    meal = Meal_offerings.query.get_or_404(meal_id)
    return render_template('6.Pick_Up.html', meal=meal)


@main.route('/meal/<int:meal_id>')
def meal_details(meal_id):
    meal = Meal_offerings.query.get_or_404(meal_id)
    vendor = User.query.get(meal.vendor_id)
    reviews = Review.query.filter_by(meal_id=meal_id).all()
    return render_template('meal_details.html', meal=meal, vendor=vendor, reviews=reviews)
