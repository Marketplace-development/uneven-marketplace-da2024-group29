from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app
from .models import db, User, Vendor, Customer, Meal_offerings, Review, CuisineType, Transaction #, TransactionStatus
import os  # For working with file paths
import datetime
from supabase import create_client, Client  # For connecting to Supabase
from datetime import datetime
import re
import requests
from math import radians, cos, sin, sqrt, atan2
from urllib.parse import quote

SUPABASE_URL = "https://rniucvwgcukfmgiscgzj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJuaXVjdndnY3VrZm1naXNjZ3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzA4OTcyNDQsImV4cCI6MjA0NjQ3MzI0NH0.8ukVk16UcFWMS6r6cfDGefE2hTkQGia8v53luWNRBRc"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


main = Blueprint('main', __name__)

def get_coordinates(address):
    """
    Roept de Google Maps API aan om de coördinaten van een adres op te halen.
    """
    #api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')
    api_key = 'AIzaSyDZoTidAslIv8u7dHvcY9_AdLaE5f8Nikw'
    if not api_key:
        current_app.logger.error("Google Maps API key is missing!")
        return None, None

    # Encode het adres voor URL-veiligheid
    encoded_address = quote(address)

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
    print(f"Google Maps API URL: {url}")  # Dit toont de URL voor handmatige debugging

    response = requests.get(url)

    if response.status_code != 200:
        current_app.logger.error(f"Google Maps API request failed. Status code: {response.status_code}")
        print(f"API Response: {response.text}")  # Dit toont het volledige API-response voor debugging
        return None, None

    data = response.json()
    if data.get("status") != "OK":
        error_message = data.get("error_message", "Unknown error")
        current_app.logger.error(f"Google Maps API returned an error: {error_message}")
        return None, None

    # Extract coordinates
    results = data.get("results")
    if results:
        location = results[0]['geometry']['location']
        return location['lat'], location['lng']
    
    current_app.logger.error(f"No results found for address: {address}")
    return None, None




def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Bereken de afstand in kilometers tussen twee geografische punten.
    """
    R = 6371  # Aarde straal in kilometers

    if lat2 is None or lon2 is None:
    # Stel bijvoorbeeld een standaardlocatie in of sla het proces over
        lat2, lon2 = 51.04849945776606, 3.7287827734729975 #coordinaten de crook

    # Controleer of geen van de coördinaten None is
    if None not in [lat1, lon1, lat2, lon2]:
        # Als alle coördinaten geldig zijn, converteer ze naar radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    else:
        # Log de waarde van de coördinaten voor debugging
        print(f"Fout: Ongeldige coördinaten - lat1: {lat1}, lon1: {lon1}, lat2: {lat2}, lon2: {lon2}")
        raise ValueError(f"Een van de coördinaten is ongeldig (None): lat1={lat1}, lon1={lon1}, lat2={lat2}, lon2={lon2}.")

    # Bereken de verschillen in breedte- en lengtegraad
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Bereken de afstand met de Haversine-formule
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Bereken de uiteindelijke afstand
    distance = R * c
    return distance



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
        
         # Volledig adres samenstellen
        full_address = f"{street} {number}, {zip} {city}"

        # Coördinaten ophalen via de Google Maps API
        latitude, longitude = get_coordinates(full_address)

        latitude = latitude if latitude is not None else 0.0
        longitude = longitude if longitude is not None else 0.0

        if latitude == 0.0 and longitude == 0.0:
            flash("Unable to retrieve coordinates for the provided address. Using default coordinates (0,0).")


        
        # Als de gebruiker niet bestaat, voeg toe aan de database
        new_user = User(
            username=username,
            email=email,
            street=street,
            number=number,
            zip=zip,
            city=city,
            latitude=latitude,   
            longitude=longitude,
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
        username = request.form['username'].strip()
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
        expiry_date_str = request.form.get('expiry_date') 

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
        
        expiry_date = None
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Invalid date format for expiry date.", "error")
                return redirect(url_for('main.add_meal'))
        # Create the new meal record in the database
        new_meal = Meal_offerings(
            name=name,
            description=description,
            picture=picture_url,  # Store the URL or file path to the uploaded image
            vendor_id=user_id,
            cuisine=CuisineType[cuisine],
            expiry_date = expiry_date
        )

        # Commit the meal record to the database
        db.session.add(new_meal)
        db.session.commit()

        

        # Flash a success message and redirect to the index page
        flash("Meal added successfully!", "success")
        return redirect(url_for('main.index'))

    # Render the meal creation page if it's a GET request
    return render_template('4.Meal_Creation.html', cuisines=CuisineType)

# Begin van algoritme filteren op keuken/stad/beoordeling
@main.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op
        city = user.city  # Haal de stad van de ingelogde gebruiker op
        latitude = user.latitude  # De breedtegraad van de gebruiker
        longitude = user.longitude  # De lengtegraad van de gebruiker
        cuisine_filter = request.args.get('cuisine', 'ALL')  # Haal het cuisine filter op
        distance_param = request.args.get('distance', '50')  # Haal de afstand op (default 50 km)
        
        try:
            distance_filter = float(distance_param)
        except ValueError:
            distance_filter = 50.0
        
        # Haal alle maaltijden (MealOffering) op en filteren op cuisine
        meal_offerings = Meal_offerings.query.all()

        # Filteren op cuisine
        if cuisine_filter != 'ALL':
            try:
                selected_cuisine = CuisineType(cuisine_filter)  # Converteer naar enum
                selected_cuisine_upper = selected_cuisine
                meal_offerings = [
                    meal for meal in meal_offerings if meal.cuisine == selected_cuisine_upper
                ]
            except KeyError:
                # Ongeldig cuisine_filter (fallback naar geen resultaten)
                meal_offerings = []

    
        # Filteren op afstand
        filtered_meals = []
        for meal in meal_offerings:
            vendor = User.query.get(meal.vendor_id)
            if vendor:
                # Combineer de adresvelden van de vendor om het volledige adres te krijgen
                vendor_address = f"{vendor.street} {vendor.number}, {vendor.zip} {vendor.city}"
                # Verkrijg de coördinaten van de vendor
                lat, lon = get_coordinates(vendor_address)
                if lat and lon:
                    # Bereken de afstand tussen de gebruiker en de vendor
                    distance = calculate_distance(latitude, longitude, lat, lon)
                    if distance <= float(distance_filter):  # Filteren op de ingestelde afstand
                        # Voeg de berekende afstand toe aan de maaltijdgegevens
                        meal.distance = round(distance, 2)  # Rond de afstand af voor betere leesbaarheid
                        filtered_meals.append(meal)
        
        # Filteren op stad
        # local_meals = [meal for meal in meal_offerings if User.city == city]  # Lokale maaltijden
        # other_meals = [meal for meal in meal_offerings if User.city != city]  # Andere maaltijden
        # meal_offerings_sorted = local_meals + other_meals  # Lokale maaltijden bovenaan

        # Bereken de gemiddelde beoordeling voor maaltijden
        # def get_average_rating(meal_id):
            # reviews = Review.query.filter_by(meal_id=meal_id).all()
            # if reviews:
                # total_score = sum(review.score for review in reviews)
                # return total_score / len(reviews)
            # return 0

        # Sorteer maaltijden op basis van beoordeling
        # meal_offerings_sorted = sorted(meal_offerings_sorted, key=lambda Meal_offerings: get_average_rating(Meal_offerings.meal_id), reverse=True)

        return render_template('index.html', username=User.username, listings=filtered_meals)
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
    # Controleer of user_id al bestaat in Vendors.vendor_id
    existing_customer = Customer.query.filter_by(customer_id=user_id).first()

    if not existing_customer:
        # Als de gebruiker nog geen vendor is, voeg toe
        customer = Customer(customer_id=user_id, amount = 1)
        db.session.add(customer)
    else:
        existing_customer.amount += 1

    # Update de maaltijdstatus naar 'NOT_AVAILABLE'
    meal.status = "NOT_AVAILABLE" #is dit nodig aangezien paar lijnen later de status op claimed gezet wordt?

    transaction = Transaction(
        meal_id=meal_id,
        customer_id=user_id,
        vendor_id=meal.vendor_id
        )
    meal.status = "CLAIMED"
    db.session.add(transaction)
    db.session.commit()

    
    flash("Meal successfully claimed!", "success")
    return redirect(url_for('main.pick_up', meal_id=meal_id))

@main.route('/pick-up/<int:meal_id>', methods=['GET'])
def pick_up(meal_id):
    # Haal de maaltijd op
    meal = Meal_offerings.query.get_or_404(meal_id)
    
    # Haal de vendor op die de maaltijd heeft aangeboden
    vendor = User.query.get(meal.vendor_id)
    if not vendor:
        flash("Vendor not found.", "error")
        return redirect(url_for('main.index'))
    
    # Geef zowel de maaltijd als de vendor door aan de template
    return render_template('6.Pick_Up.html', meal=meal, vendor=vendor)


@main.route('/meal/<int:meal_id>')
def meal_details(meal_id):
    meal = Meal_offerings.query.get_or_404(meal_id)
    vendor = User.query.get(meal.vendor_id)
    reviews = Review.query.filter_by(meal_id=meal_id).all()
    return render_template('meal_details.html', meal=meal, vendor=vendor, reviews=reviews)
