from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from .models import db, User, Vendor, Customer, Meal_offerings, Review, CuisineType, MealStatus, Transaction, TransactionStatus
import os  # For working with file paths
from supabase import create_client, Client  # For connecting to Supabase



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

def upload_to_supabase_storage(file, file_path):
    """Upload the image to Supabase storage and return the URL or file path."""
    response = supabase.storage.from_('meal_picture').upload(file_path, file)
    if response.status_code == 200:
        return supabase.storage.from_('meal_picture').get_public_url(file_path)['publicURL']
    else:
        raise Exception("Failed to upload file")

@main.route('/add-meal', methods=['GET', 'POST'])
def add_meal():
    if request.method == 'POST':
        # Retrieve meal details from the form
        name = request.form['name']
        description = request.form['description']
        picture = request.files['picture'] if 'picture' in request.files else None
        cuisine = request.form['cuisine']

        # Validation: Ensure both name and cuisine are provided
        if not name or not cuisine:
            flash("Meal name and cuisine type are required!", "error")
            return redirect(url_for('main.add_meal'))
        
        # Vendor ID is retrieved from session
        vendor_id = session.get('user_id')
        if not vendor_id:
            flash("You must be logged in to add a meal.", "error")
            return redirect(url_for('main.login'))

        # Upload picture to Supabase if provided
        picture_url = None
        if picture:
            file_path = f"meal_picture/{picture.filename}"
            picture_url = upload_to_supabase_storage(picture, file_path)

        # Create the new meal record in the database
        new_meal = Meal_offerings(
            name=name,
            description=description,
            picture=picture_url,  # Store the URL or file path to the uploaded image
            status=MealStatus.AVAILABLE,  # Default status is available
            vendor_id=vendor_id,
            cuisine=CuisineType[cuisine]  # Map the cuisine to its enum
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



#Begin van algoritme filteren op keuken/stad/beoordeling
@main.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op
        city = user.city  # Haal de stad van de ingelogde gebruiker op
        cuisine_filter = request.args.get('cuisine', None)  # Haal het cuisine filter op
        
        # Haal alle maaltijden (MealOffering) op en filteren op cuisine
        meal_offerings = Meal_offerings.query.all()

        # Filteren op cuisine (keuken)
        if cuisine_filter:
            meal_offerings = [meal for meal in meal_offerings if Meal_offerings.cuisine == CuisineType[cuisine_filter]]

        # Filteren op stad
        local_meals = [meal for meal in meal_offerings if Meal_offerings.vendor.city == city]  # Lokale maaltijden
        other_meals = [meal for meal in meal_offerings if Meal_offerings.vendor.city != city]  # Andere maaltijden
        meal_offerings_sorted = local_meals + other_meals  # Lokale maaltijden bovenaan

        # Bereken de gemiddelde beoordeling voor maaltijden
        def get_average_rating(meal_id):
            reviews = Review.query.filter_by(meal_id=meal_id).all()
            if reviews:
                total_score = sum(review.score for review in reviews)
                return total_score / len(reviews)
            return 0

        # Sorteer maaltijden op basis van beoordeling
        meal_offerings_sorted = sorted(meal_offerings_sorted, key=lambda Meal_offerings: get_average_rating(Meal_offerings.meal_id), reverse=True)

        return render_template('index.html', username=User.username, listings=meal_offerings_sorted)
    else:
        return redirect(url_for('main.login'))  # Als de gebruiker niet is ingelogd, stuur naar loginpagina
