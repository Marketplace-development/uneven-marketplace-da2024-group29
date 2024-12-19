from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app
from .models import db, User, Vendor, Customer, Meal_offerings, Review, CuisineType, Transaction, MealStatus
import os 
from supabase import create_client, Client
from datetime import datetime, timedelta, date, time
import re
import requests
from math import radians, cos, sin, sqrt, atan2
from urllib.parse import quote

SUPABASE_URL = "https://rniucvwgcukfmgiscgzj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJuaXVjdndnY3VrZm1naXNjZ3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzA4OTcyNDQsImV4cCI6MjA0NjQ3MzI0NH0.8ukVk16UcFWMS6r6cfDGefE2hTkQGia8v53luWNRBRc"


supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


main = Blueprint("main", __name__)


def get_coordinates(address):
    api_key = "AIzaSyDZoTidAslIv8u7dHvcY9_AdLaE5f8Nikw"
    if not api_key:
        current_app.logger.error("Google Maps API key is missing!")
        return None, None

    encoded_address = quote(address)

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    response = requests.get(url)

    if response.status_code != 200:
        current_app.logger.error(f"Google Maps API request failed. Status code: {response.status_code}")
        print(f"API Response: {response.text}")
        return None, None

    data = response.json()
    if data.get("status") != "OK":
        error_message = data.get("error_message", "Unknown error")
        current_app.logger.error(f"Google Maps API returned an error: {error_message}")
        return None, None

    results = data.get("results")
    if results:
        location = results[0]["geometry"]["location"]
        return location["lat"], location["lng"]
    
    current_app.logger.error(f"No results found for address: {address}")
    return None, None


def get_distances(origin, destinations, api_key):
    destinations_str = '|'.join(destinations)
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
    for row in data.get("rows", []):
        for element in row.get("elements", []):
            if element.get("status") == "OK":
                distances.append(element["distance"]["value"])
            else:
                distances.append(None)
    return distances



def mark_expired_meals():
    available_meals = Meal_offerings.query.filter_by(status=MealStatus.AVAILABLE).all()
    print(f"DEBUG - Available Meals: {len(available_meals)}")

    for meal in available_meals:
        print(f"DEBUG - Checking Meal ID: {meal.meal_id}, Name: {meal.name}")
        meal.mark_as_expired()
    
    db.session.commit()



@main.route("/register", methods=["GET", "POST"])
def register():
    print(f"Session user_id: {session.get('user_id')}")

    if request.method == "POST":
        username = request.form.get("username").strip() 
        email = request.form.get("email").strip()
        street = request.form.get("street").strip()
        number = request.form.get("number").strip()
        zip = request.form.get("zip").strip()
        city = request.form.get("city").strip()

        if not username or not email or not street or not number or not zip or not city:
            flash("All fields are required!")
            return redirect(url_for("main.register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("User already exists. Please choose a different username or log in.")
            return redirect(url_for("main.register"))
        
        full_address = f"{street} {number}, {zip} {city}"

        latitude, longitude = get_coordinates(full_address)

        if latitude is None or longitude is None:
            flash("Address not found. Please check the address and try again.")
            return redirect(url_for("main.register"))

        latitude = latitude if latitude is not None else 0.0
        longitude = longitude if longitude is not None else 0.0

        if latitude == 0.0 and longitude == 0.0:
            flash("Unable to retrieve coordinates for the provided address. Using default coordinates (0,0).")

        new_user = User(
            username=username,
            email=email,
            street=street,
            number=number,
            zip=zip,
            city=city,
            latitude=latitude,   
            longitude=longitude,
            type="user"
        )  

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.user_id
        vendor_id = new_user.user_id
        customer_id = new_user.user_id

        flash("Registration successful!", "success")
        return redirect(url_for("main.index"))
        
    return render_template("Register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    print(f"Session user_id: {session.get('user_id')}") 

    if request.method == "POST":
        username = request.form["username"].strip()
        user = User.query.filter_by(username=username).first() 
        if user:
            session["user_id"] = user.user_id 
            return redirect(url_for("main.index"))  
        flash("User not found, please try again.")
    return render_template("Login.html") 


@main.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None) 
    return redirect(url_for("main.about_us"))


@main.route("/base")
def base():
    return render_template("base.html")

def upload_to_supabase_storage(bucket_name, file, filename):
    response = supabase.storage.from_(bucket_name).upload(filename, file)
    if response.get("error"):
        print("Error uploading file:", response["error"])
        return None
    return supabase.storage.from_(bucket_name).get_public_url(filename)

@main.route("/add-meal", methods=["GET", "POST"])
def add_meal():
    user_id = session.get("user_id")
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        picture = request.files.get("picture")
        cuisine = request.form.get("cuisine")
        pickup_date = request.form.get("pickup_date")
        pickup_start_time = request.form.get("pickup_start_time")
        pickup_end_time = request.form.get("pickup_end_time")

        if not all([name, description, cuisine, pickup_date, pickup_start_time, pickup_end_time]):
            flash("Fill in required fields!", "error")
            return redirect(url_for("main.add_meal"))
        
        if not user_id:
            flash("You must be logged in to add a meal.", "error")
            return redirect(url_for("main.login"))

        try:
            parsed_date = datetime.strptime(pickup_date, "%Y-%m-%d").date()
            start_time = datetime.strptime(pickup_start_time, "%H:%M").time()
            end_time = datetime.strptime(pickup_end_time, "%H:%M").time()

            if end_time <= start_time:
                flash("Pickup end time must be later than the start time.", "error")
                return redirect(url_for("main.add_meal"))
        except ValueError:
            flash("Invalid date or time format.", "error")
            return redirect(url_for("main.add_meal"))

        picture_url = "static/pictures/logo.png"
        if picture:
            def sanitize_filename(filename):
                cleaned_filename = re.sub(r'[^\w\-_\.]', '_', filename)
                return cleaned_filename
            
            original_filename = picture.filename
            sanitized_filename = sanitize_filename(original_filename)

            filename = f"{user_id}_{datetime.utcnow().isoformat()}_{sanitized_filename}"
            
            response = supabase.storage.from_("picture").upload(filename, picture.read())
            if not response:
                flash("Error uploading image to Supabase.", "error")
                return redirect(url_for("main.add_meal"))
            picture_url = supabase.storage.from_("picture").get_public_url(filename)

        existing_vendor = Vendor.query.filter_by(vendor_id=user_id).first()

        if not existing_vendor:
            vendor = Vendor(vendor_id=user_id)
            db.session.add(vendor)
            db.session.commit()

        new_meal = Meal_offerings(
            name=name,
            description=description,
            picture=picture_url, 
            vendor_id=user_id,
            cuisine=CuisineType[cuisine],
            pickup_date = parsed_date,
            pickup_start_time = start_time,
            pickup_end_time = end_time
        )

        db.session.add(new_meal)
        db.session.commit()

        flash("Meal added successfully!", "success")
        return redirect(url_for("main.index"))

    return render_template("Share_Meal.html", cuisines=CuisineType)


@main.route('/', methods=["GET", "POST"])
def index():
    if "user_id" in session:
        user = User.query.get(session["user_id"])

        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)


        mark_expired_meals()

        meal_offerings = Meal_offerings.query.filter(
            Meal_offerings.status == MealStatus.AVAILABLE,
            Meal_offerings.vendor_id != user.user_id
            ).all()

        origin = f"{user.latitude},{user.longitude}"
        cuisine_filter = request.args.get("cuisine", "ALL")
        distance_param = request.args.get("distance", "1000000")
        
        try:
            distance_filter = float(distance_param)
        except ValueError:
            distance_filter = 1000000.0

        meal_offerings = Meal_offerings.query.filter_by(status="AVAILABLE").all()

        meal_offerings.sort(
            key=lambda meal: (
                meal.pickup_date or date.max,
                meal.pickup_end_time or time.max
            )
        )

        if cuisine_filter != "ALL":
            try:
                selected_cuisine = CuisineType(cuisine_filter)
                meal_offerings = [
                    meal for meal in meal_offerings if meal.cuisine == selected_cuisine
                ]
            except KeyError:
                meal_offerings = []

        destinations = []
        vendor_mapping = {}
        for meal in meal_offerings:
            vendor = User.query.get(meal.vendor_id)
            if vendor:
                vendor_coords = f"{vendor.latitude},{vendor.longitude}"
                destinations.append(vendor_coords)
                vendor_mapping[vendor_coords] = meal

        api_key = "AIzaSyDZoTidAslIv8u7dHvcY9_AdLaE5f8Nikw"
        distances = get_distances(origin, destinations, api_key)

        filtered_meals = []
        if distances:
            for distance, coords in zip(distances, destinations):
                if distance and distance / 1000 <= distance_filter:
                    meal = vendor_mapping[coords]
                    meal.distance = round(distance / 1000, 2)
                    filtered_meals.append(meal)

        return render_template(
            "index.html",
            username=user.username,
            listings=filtered_meals,
            user=user,
            cuisine=cuisine_filter,
            distance=distance_filter,
            today=today,
            tomorrow=tomorrow,
            datetime=datetime
            )
    else:
        return redirect(url_for("main.about_us"))


@main.route("/meal/<int:meal_id>", methods=["GET", "POST"])
def meal_details(meal_id):
    meal = Meal_offerings.query.get_or_404(meal_id)
    vendor = User.query.get(meal.vendor_id)
    reviews = Review.query.filter_by(meal_id=meal_id).first()
    average_rating = Vendor.query.get(meal.vendor_id).average_rating

    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    return render_template(
        "meal_details.html",
        meal=meal,
        vendor=vendor,
        reviews=reviews,
        average_rating=average_rating,
        today=today,
        tomorrow=tomorrow
    )


@main.route("/claim-meal/<int:meal_id>", methods=["POST"])
def claim_meal(meal_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to claim a meal.", "error")
        return redirect(url_for("main.login"))

    meal = Meal_offerings.query.get_or_404(meal_id)

    if meal.vendor_id == user_id:
        flash("You cannot claim your own meal!", "error")
        return redirect(url_for("main.index"))

    existing_customer = Customer.query.filter_by(customer_id=user_id).first()

    if not existing_customer:
        customer = Customer(customer_id=user_id, amount = 1)
        db.session.add(customer)
    else:
        existing_customer.amount += 1

    transaction = Transaction(
        meal_id=meal_id,
        customer_id=user_id,
        vendor_id=meal.vendor_id
        )
    meal.status = "CLAIMED"
    db.session.add(transaction)
    db.session.commit()
    
    flash("Meal successfully claimed!", "success")
    return redirect(url_for("main.index", meal_id=meal_id))


@main.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access the profile.", "error")
        return redirect(url_for("main.login"))

    user = User.query.get_or_404(user_id)
    vendor = Vendor.query.filter_by(vendor_id=user_id).first()
    average_rating = round(vendor.average_rating, 2) if vendor and vendor.average_rating else None

    if request.method == "POST":
        username = request.form.get("username").strip() 
        email = request.form.get("email").strip()
        street = request.form.get("street").strip()
        number = request.form.get("number").strip()
        zip = request.form.get("zip").strip()
        city = request.form.get("city").strip()

        if not all([username, email, street, number, zip, city]):
            flash("All fields are required.", "danger")
            return redirect(url_for("main.profile"))

        if '@' not in email or '.' not in email:
            flash("Invalid email format.", "danger")
            return redirect(url_for("main.profile"))

        try:
            user.username = username
            user.email = email
            user.street = street
            user.number = number
            user.zip = zip
            user.city = city

            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating your profile. Please try again.")

        return redirect(url_for("main.profile"))

    shared_meals = db.session.query(Meal_offerings, Transaction.created_at).outerjoin(
        Transaction, Meal_offerings.meal_id == Transaction.meal_id
    ).filter(Meal_offerings.vendor_id == user_id, Meal_offerings.status == "AVAILABLE").all()

    shared_meals_data = [
        {
            "id": meal.meal_id,
            "name": meal.name,
            "description": meal.description,
            "picture": meal.picture,
            "status": meal.status,
            "claimed_date": transaction_created_at,
            "reviews": Review.query.filter_by(meal_id=meal.meal_id).all()
        }
        for meal, transaction_created_at in shared_meals
    ]

    claimed_meals = db.session.query(Meal_offerings, Vendor, Transaction).join(
        Transaction, Transaction.meal_id == Meal_offerings.meal_id
    ).join(
        Vendor, Vendor.vendor_id == Meal_offerings.vendor_id
    ).filter(
        Transaction.customer_id == user_id,
        Meal_offerings.status == "CLAIMED"
    ).all()

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

    expired_meals = Meal_offerings.query.filter_by(
        vendor_id=user_id,
        status="EXPIRED"
        ).all()

    expired_meals_data = [
        {
            "id": meal.meal_id,
            "name": meal.name,
            "description": meal.description,
            "picture": meal.picture,
            "pickup_date": meal.pickup_date.strftime("%d-%m-%Y") if meal.pickup_date else "N/A",
            "pickup_time": f"{meal.pickup_start_time.strftime('%H:%M')} - {meal.pickup_end_time.strftime('%H:%M')}" if meal.pickup_start_time and meal.pickup_end_time else "N/A",
        }
        for meal in expired_meals
    ]

    deleted_meals = Meal_offerings.query.filter_by(
        vendor_id=user_id,
        status="DELETED"
    ).all()

    deleted_meals_data = [
        {
            "id": meal.meal_id,
            "name": meal.name,
            "description": meal.description,
            "picture": meal.picture,
            "deleted_date": meal.deleted_at.strftime("%d-%m-%Y") if meal.deleted_at else "N/A",
        }
        for meal in deleted_meals
    ]
    
    return render_template(
        "profile.html",
        user=user,
        average_rating=average_rating,
        shared_meals=shared_meals_data,
        claimed_meals=claimed_meals_data,
        expired_meals=expired_meals_data,
        deleted_meals=deleted_meals_data
    )


@main.route("/delete_meal/<int:meal_id>", methods=["POST"])
def delete_meal(meal_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to perform this action.", "error")
        return redirect(url_for("main.login"))

    meal = Meal_offerings.query.filter_by(meal_id=meal_id, vendor_id=user_id).first()
    if not meal:
        flash("Meal not found or you are not authorized to delete it.", "danger")
        return redirect(url_for("main.profile"))

    try:
        meal.status = MealStatus.DELETED
        meal.deleted_at = datetime.utcnow()
        db.session.commit()
        flash("Meal deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the meal. Please try again.", "danger")

    
    return redirect(url_for("main.profile"))

@main.route("/rate-vendor/<int:vendor_id>", methods=["POST"])
def rate_vendor(vendor_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to rate vendors.", "error")
        return redirect(url_for("main.login"))

    rating = int(request.form["rating"])
    meal_id = int(request.form["meal_id"])  
    if rating < 0 or rating > 5:
        flash("Rating must be between 0 and 5.", "error")
        return redirect(url_for("main.profile"))
    
    existing_review = Review.query.filter_by(meal_id=meal_id).first()
    if existing_review:
        flash(f"Given rating: {existing_review.score}", "info")
        return redirect(url_for("main.profile"))

    review = Review(vendor_id=vendor_id, customer_id=user_id, meal_id=meal_id, score=rating)
    db.session.add(review)

    vendor_reviews = Review.query.filter_by(vendor_id=vendor_id).all()
    if vendor_reviews:
        average_rating = sum(r.score for r in vendor_reviews) / len(vendor_reviews)
        vendor = Vendor.query.get(vendor_id)
        vendor.average_rating = average_rating

    db.session.commit()
    flash(f"Rating submitted successfully! Given rating: {rating}", "success")
    return redirect(url_for("main.profile"))


@main.route("/about-us")
def about_us():
    return render_template("about_us.html")


@main.route("/api/available-meals")
def available_meals():
    available_meals = Meal_offerings.query.filter_by(status=MealStatus.AVAILABLE).all()

    meals_data = []
    for meal in available_meals:
        vendor = User.query.get(meal.vendor_id)
        if vendor and vendor.latitude and vendor.longitude:
            meals_data.append({
                "meal_id": meal.meal_id,
                "name": meal.name,
                "latitude": vendor.latitude,
                "longitude": vendor.longitude,
                "description": meal.description or "No description available",
                "pickup_date": meal.pickup_date.strftime("%d-%m-%Y") if meal.pickup_date else "N/A",
                "vendor_name": vendor.username
            })

    return {"meals": meals_data}


@main.route("/meal-map")
def meal_map():
    return render_template("meal_map.html")
