from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app
from .models import db, User, Vendor, Customer, Meal_offerings, Review, CuisineType, Transaction, MealStatus
import os  # For working with file paths
import datetime
from supabase import create_client, Client  # For connecting to Supabase
from datetime import datetime
import re
import requests
from math import radians, cos, sin, sqrt, atan2
from urllib.parse import quote
from datetime import date, time

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




def get_distances(origin, destinations, api_key):
    """
    Roept de Google Distance Matrix API aan om afstanden tussen een oorsprong en bestemmingen te berekenen.
    :param origin: String, coördinaten van de oorsprong in de vorm "lat,lng".
    :param destinations: Lijst van strings, elk in de vorm "lat,lng".
    :param api_key: Je Google API-sleutel.
    :return: Lijst van afstanden (in meters) of None als er een fout is.
    """
    destinations_str = '|'.join(destinations)  # Combineer alle bestemmingen in een string
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={quote(origin)}&destinations={quote(destinations_str)}&key={api_key}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"API request failed: {response.status_code}")
        return None

    data = response.json()
    if data.get("status") != "OK":
        print(f"API error: {data.get('error_message', 'Unknown error')}")
        return None

    distances = []
    for row in data.get('rows', []):
        for element in row.get('elements', []):
            if element.get('status') == 'OK':
                distances.append(element['distance']['value'])  # Afstand in meters
            else:
                distances.append(None)
    return distances



def mark_expired_meals():
    """
    Controleer alle maaltijden en markeer degenen die zijn verlopen als EXPIRED.
    """
    # Haal alle maaltijden op met status AVAILABLE
    available_meals = Meal_offerings.query.filter_by(status=MealStatus.AVAILABLE).all()
    print(f"DEBUG - Available Meals: {len(available_meals)}")

    for meal in available_meals:
        print(f"DEBUG - Checking Meal ID: {meal.meal_id}, Name: {meal.name}")
        meal.mark_as_expired()
    
    # Sla de wijzigingen op in de database
    db.session.commit()



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

        if latitude is None or longitude is None:
            # Flashmelding als het adres niet gevonden kan worden
            flash("Address not found. Please check the address and try again.")
            # Zorg ervoor dat de rest van de velden behouden blijven, behalve het adres
            return render_template('2. Signup.html', username=username, email=email, street=street, number=number, zip=zip, city=city)

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
    return redirect(url_for('main.about_us'))  # Na uitloggen, stuur naar de loginpagina


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
        pickup_date = request.form.get('pickup_date')
        pickup_start_time = request.form.get('pickup_start_time')
        pickup_end_time = request.form.get('pickup_end_time')
        # expiry_date_str = request.form.get('expiry_date') 

        # Validation: Ensure both name and cuisine are provided
        if not name or not cuisine:
            flash("Fill in required fields!", "error")
            return redirect(url_for('main.add_meal'))
        
        if not user_id:
            flash("You must be logged in to add a meal.", "error")
            return redirect(url_for('main.login'))

        # Parse and validate the date and times
        try:
            parsed_date = datetime.strptime(pickup_date, '%Y-%m-%d').date()
            start_time = datetime.strptime(pickup_start_time, '%H:%M').time()
            end_time = datetime.strptime(pickup_end_time, '%H:%M').time()

            # Ensure the end time is later than the start time
            if end_time <= start_time:
                flash("Pickup end time must be later than the start time.", "error")
                return redirect(url_for('main.add_meal'))
        except ValueError:
            flash("Invalid date or time format.", "error")
            return redirect(url_for('main.add_meal'))

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
        
        # expiry_date = None
        # if expiry_date_str:
            # try:
                # expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            # except ValueError:
                # flash("Invalid date format for expiry date.", "error")
                # return redirect(url_for('main.add_meal'))
        # Create the new meal record in the database
        new_meal = Meal_offerings(
            name=name,
            description=description,
            picture=picture_url,  # Store the URL or file path to the uploaded image
            vendor_id=user_id,
            cuisine=CuisineType[cuisine],
            pickup_date = parsed_date,
            pickup_start_time = start_time,
            pickup_end_time = end_time
            # expiry_date = expiry_date
        )

        # Commit the meal record to the database
        db.session.add(new_meal)
        db.session.commit()
        
        # Flash a success message and redirect to the index page
        flash("Meal added successfully!", "success")
        return redirect(url_for('main.index'))

    # Render the meal creation page if it's a GET request
    return render_template('4.Meal_Creation.html', cuisines=CuisineType)



# Begin van algoritme filteren op keuken/stad/beoordeling (sorteert standaard op kortste ophaaldatum)
@main.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op

        # Markeer vervallen maaltijden
        mark_expired_meals()
        
        # Haal beschikbare maaltijden op
        meal_offerings = Meal_offerings.query.filter_by(status=MealStatus.AVAILABLE).all()
        print(f"DEBUG - Available Meals after marking expired: {len(meal_offerings)}")

        origin = f"{user.latitude},{user.longitude}"  # Gebruiker's coördinaten als oorsprong
        cuisine_filter = request.args.get('cuisine', 'ALL')
        distance_param = request.args.get('distance', '1000000')
        
        try:
            distance_filter = float(distance_param)
        except ValueError:
            distance_filter = 1000000.0

        meal_offerings = Meal_offerings.query.filter_by(status='AVAILABLE').all()

        meal_offerings.sort(
            key=lambda meal: (
                meal.pickup_date or date.max,
                meal.pickup_end_time or time.max
            )
        )

        # Filter op cuisine
        if cuisine_filter != 'ALL':
            try:
                selected_cuisine = CuisineType(cuisine_filter)
                meal_offerings = [
                    meal for meal in meal_offerings if meal.cuisine == selected_cuisine
                ]
            except KeyError:
                meal_offerings = []

        # Bereid bestemmingen voor (alle vendor-adressen)
        destinations = []
        vendor_mapping = {}
        for meal in meal_offerings:
            vendor = User.query.get(meal.vendor_id)
            if vendor:
                vendor_coords = f"{vendor.latitude},{vendor.longitude}"
                destinations.append(vendor_coords)
                vendor_mapping[vendor_coords] = meal

        # Gebruik Distance Matrix API om afstanden te berekenen
        api_key = 'AIzaSyDZoTidAslIv8u7dHvcY9_AdLaE5f8Nikw'
        distances = get_distances(origin, destinations, api_key)

        # Filter op afstand
        filtered_meals = []
        if distances:
            for distance, coords in zip(distances, destinations):
                if distance and distance / 1000 <= distance_filter:  # Converteer naar kilometers
                    meal = vendor_mapping[coords]
                    meal.distance = round(distance / 1000, 2)  # Converteer naar kilometers en afronden
                    filtered_meals.append(meal)

        return render_template('index.html', username=user.username, listings=filtered_meals, user=user, cuisine=cuisine_filter, distance=distance_filter)
    else:
        return redirect(url_for('main.about_us'))





#hieronder staat de originele code zonder filteren op
#@main.route('/', methods=['GET', 'POST'])
#def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op
        city = user.city  # Haal de stad van de ingelogde gebruiker op
        latitude = user.latitude  # De breedtegraad van de gebruiker
        longitude = user.longitude  # De lengtegraad van de gebruiker
        cuisine_filter = request.args.get('cuisine', 'ALL')  # Haal het cuisine filter op
        distance_param = request.args.get('distance', '1000000')  # Haal de afstand op (default 1000000)

        try:
            distance_filter = float(distance_param)
        except ValueError:
            distance_filter = 1000000.0
        
        # Haal alle maaltijden (MealOffering) op
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
                    if distance <= distance_filter:  # Filteren op de ingestelde afstand
                        # Voeg de berekende afstand toe aan de maaltijdgegevens
                        meal.distance = round(distance, 2)  # Rond de afstand af voor betere leesbaarheid
                        filtered_meals.append(meal)
        
        return render_template('index.html', username=User.username, listings=filtered_meals, user=user, cuisine=cuisine_filter, distance=distance_filter)
    else:
        return redirect(url_for('main.about_us'))  # Als de gebruiker niet is ingelogd, stuur naar loginpagina






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

    transaction = Transaction(
        meal_id=meal_id,
        customer_id=user_id,
        vendor_id=meal.vendor_id
        # pickup_time=pickup_time
        )
    meal.status = "CLAIMED"
    db.session.add(transaction)
    db.session.commit()
    
    flash("Meal successfully claimed!", "success")
    return redirect(url_for('main.profile', meal_id=meal_id)) # hier krijg ik een error en zegt het dat er main.profile moet staan

@main.route('/meal/<int:meal_id>', methods=['GET', 'POST'])
def meal_details(meal_id):
    meal = Meal_offerings.query.get_or_404(meal_id)
    vendor = User.query.get(meal.vendor_id)
    reviews = Review.query.filter_by(meal_id=meal_id).first()
    average_rating = Vendor.query.get(meal.vendor_id).average_rating
    return render_template('meal_details.html', meal=meal, vendor=vendor, reviews=reviews,  average_rating=average_rating)

@main.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to access the profile.", "error")
        return redirect(url_for('main.login'))

    # Fetch the logged-in user's details
    user = User.query.get_or_404(user_id)
    vendor = Vendor.query.filter_by(vendor_id=user_id).first()
    average_rating = round(vendor.average_rating, 2) if vendor and vendor.average_rating else None

    if request.method == 'POST':
        # Handle form submission to update user profile
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        street = request.form['street'].strip()
        number = request.form['number'].strip()
        zip_code = request.form['zip'].strip()
        city = request.form['city'].strip()

        # Validate required fields
        if not all([username, email, street, number, zip_code, city]):
            flash("All fields are required.", "danger")
            return redirect(url_for('main.profile'))

        # Optional: Add email format validation (basic example)
        if "@" not in email or "." not in email:
            flash("Invalid email format.", "danger")
            return redirect(url_for('main.profile'))

        try:
            # Update user details
            user.username = username
            user.email = email
            user.street = street
            user.number = number
            user.zip = zip_code
            user.city = city

            # Commit changes to the database
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating your profile. Please try again.")

        return redirect(url_for('main.profile'))

    # Fetch shared meals for the logged-in user (status available and claimed)
    shared_meals = db.session.query(Meal_offerings, Transaction.created_at).outerjoin(
        Transaction, Meal_offerings.meal_id == Transaction.meal_id
    ).filter(Meal_offerings.vendor_id == user_id).all()

    # Prepare shared meals with claimed_date
    shared_meals_data = [
        {
            "id": meal.meal_id,
            "name": meal.name,
            "description": meal.description,
            "picture": meal.picture,
            "status": meal.status,
            "claimed_date": transaction_created_at,  # Use the created_at field from Transaction
            "reviews": Review.query.filter_by(meal_id=meal.meal_id).all()
        }
        for meal, transaction_created_at in shared_meals
    ]

    # Fetch claimed meals for the logged-in user
    claimed_meals = db.session.query(Meal_offerings, Vendor, Transaction).join(
        Transaction, Transaction.meal_id == Meal_offerings.meal_id
    ).join(
        Vendor, Vendor.vendor_id == Meal_offerings.vendor_id
    ).filter(
        Transaction.customer_id == user_id,
        Meal_offerings.status == "CLAIMED"
    ).all()

    # Prepare data for claimed meals
    claimed_meals_data = [
        {
            "id": meal.meal_id,
            "name": meal.name,
            "description": meal.description,
            "picture": meal.picture,
            "vendor_name": (User.query.get(vendor.vendor_id).username if User.query.get(vendor.vendor_id) else "Unknown Vendor"),
            "vendor_id": vendor.vendor_id,
            "claimed_date": transaction.created_at if transaction else None,
            "review": Review.query.filter_by(meal_id=meal.meal_id).first()
        }
        for meal, vendor, transaction in claimed_meals
    ]

    # Fetch expired meals (for vendor only)
    expired_meals = Meal_offerings.query.filter_by(
        vendor_id=user_id,
        status="EXPIRED"  # Status for expired meals
        ).all()

    expired_meals_data = [
        {
            "id": meal.meal_id,
            "name": meal.name,
            "description": meal.description,
            "picture": meal.picture,
            "pickup_date": meal.pickup_date.strftime('%d-%m-%Y') if meal.pickup_date else "N/A",
            "pickup_time": f"{meal.pickup_start_time.strftime('%H:%M')} - {meal.pickup_end_time.strftime('%H:%M')}" if meal.pickup_start_time and meal.pickup_end_time else "N/A",
        }
        for meal in expired_meals
    ]


    # Render the profile template
    return render_template(
        'profile.html',
        user=user,
        shared_meals=shared_meals_data,
        claimed_meals=claimed_meals_data,
        expired_meals=expired_meals_data,
        average_rating=average_rating
    )

@main.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to perform this action.", "error")
        return redirect(url_for('main.login'))

    # Fetch the meal to ensure it belongs to the logged-in user
    meal = Meal_offerings.query.filter_by(meal_id=meal_id, vendor_id=user_id).first()
    if not meal:
        flash("Meal not found or you are not authorized to delete it.", "danger")
        return redirect(url_for('main.profile'))

    try:
        meal.status = "DELETED"
        db.session.commit()
        flash("Meal marked as deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting the meal. Please try again.", "danger")
    
    return redirect(url_for('main.profile'))

@main.route('/rate-vendor/<int:vendor_id>', methods=['POST'])
def rate_vendor(vendor_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to rate vendors.', 'error')
        return redirect(url_for('main.login'))

    # Retrieve the rating and meal_id from the form
    rating = int(request.form['rating'])
    meal_id = int(request.form['meal_id'])  
    if rating < 0 or rating > 5:
        flash('Rating must be between 0 and 5.', 'error')
        return redirect(url_for('main.profile'))
    
    existing_review = Review.query.filter_by(meal_id=meal_id).first()
    if existing_review:
        flash(f'Given rating: {existing_review.score}', 'info')
        return redirect(url_for('main.profile'))
    
    # Save the rating
    review = Review(vendor_id=vendor_id, customer_id=user_id, meal_id=meal_id, score=rating)
    db.session.add(review)

    # Update the vendor's average rating
    vendor_reviews = Review.query.filter_by(vendor_id=vendor_id).all()
    if vendor_reviews:
        average_rating = sum(r.score for r in vendor_reviews) / len(vendor_reviews)
        vendor = Vendor.query.get(vendor_id)
        vendor.average_rating = average_rating

    db.session.commit()
    flash(f'Rating submitted successfully! Given rating: {rating}', 'success')
    return redirect(url_for('main.profile'))


@main.route('/about-us')
def about_us():
    return render_template('about_us.html')


#def delete_meal_with_auth(meal_id):
    #user_id = request.user_id
    #meal = meal.query.filter_by(id=meal_id, user_id=user_id).first()
    #if not meal:
     #   return {"message": "Meal not found or unauthorized"}

    #db.session.delete(meal)
    #db.session.commit()
    #flash("Meal deleted successfully")
