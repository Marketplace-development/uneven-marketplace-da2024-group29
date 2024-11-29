from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from .models import db, User, Listing, Vendor
from .models import MealOffering, Review, CuisineType   #hoort bij ons algoritme

main = Blueprint('main', __name__)

@main.route('/register', methods=['GET', 'POST'])
def register():
    print(f"Session user_id: {session.get('user_id')}")  # Toont de opgeslagen session user_id

    if request.method == 'POST':
        username = request.form['username']  # Haal de gebruikersnaam op uit het formulier

        # Controleer of de gebruiker al bestaat in de database
        if User.query.filter_by(username=username).first() is None:
            # Als de gebruiker niet bestaat, voeg deze toe aan de database
            new_user = User(username=username)
            db.session.add(new_user)
            db.session.commit()  # Sla de gebruiker op in de database

            # Zet de gebruiker in de sessie (om automatisch ingelogd te zijn)
            session['user_id'] = new_user.id
            flash("Gebruiker succesvol geregistreerd!", "success")

            # Redirect naar de indexpagina (na succesvolle registratie)
            return redirect(url_for('main.index'))
        else:
            flash("Gebruiker bestaat al, probeer een andere naam.", "error")  # Toon foutmelding
            return redirect(url_for('main.register'))  # Herlaad de registratiepagina als de naam al bestaat

    return render_template('2. Signup.html')  # Render de registratiepagina (GET-request)


# Login route: gebruikers kunnen zich hier aanmelden met hun gebruikersnaam
@main.route('/login', methods=['GET', 'POST'])
def login():
    print(f"Session user_id: {session.get('user_id')}")  # Toont de opgeslagen session user_id

    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()  # Zoek de gebruiker in de database
        if user:
            session['user_id'] = user.id  # Zet de gebruiker in de sessie
            return redirect(url_for('main.index'))  # Redirect naar de indexpagina
        flash("Gebruiker niet gevonden, probeer opnieuw.")  # Toon een foutmelding als de gebruiker niet bestaat
    return render_template('1.Login.html')  # Toon de loginpagina

# Logout route: gebruiker kan uitloggen
@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Verwijder de gebruiker uit de sessie
    return redirect(url_for('main.login'))  # Na uitloggen, stuur naar de loginpagina


@main.route('/base')
def base():
    return render_template('base.html')

@main.route('/add-meal', methods=['GET', 'POST'])
def add_meal():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        picture = request.files['picture'] if 'picture' in request.files else None
        status = request.form['status']  # Dit is automatisch ingesteld op "Beschikbaar"
        vendor_id = current_user.id  # De ingelogde gebruiker wordt als verkoper toegevoegd
        cuisine = request.form['cuisine']
        categories = request.form.getlist('categories')

        # Verwerk de afbeelding (optioneel)
        picture_filename = None
        if picture:
            picture_filename = f"static/images/{picture.filename}"
            picture.save(picture_filename)

        # Nieuwe maaltijd toevoegen aan de database
        new_meal = MealOffering(
            name=name,
            description=description,
            picture=picture_filename,
            status=status,
            vendor_id=vendor_id,
            cuisine=cuisine
        )
        db.session.add(new_meal)
        db.session.commit()

        # Koppel de maaltijd aan de geselecteerde categorieën
        for category_id in categories:
            category = Category.query.get(category_id)
            new_meal.categories.append(category)
        db.session.commit()

        return redirect(url_for('main.index'))

    vendors = Vendor.query.all()  # Dit kan eventueel weggehaald worden, omdat we vendor_id automatisch vullen.
    categories = Category.query.all()
    return render_template('4.Meal_Creation.html', categories=categories)



#Begin van algoritme filteren op keuken/stad/beoordeling
@main.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op
        city = user.Stad  # Haal de stad van de ingelogde gebruiker op
        cuisine_filter = request.args.get('cuisine', None)  # Haal het cuisine filter op
        
        # Haal alle maaltijden (MealOffering) op en filteren op cuisine
        meal_offerings = MealOffering.query.all()

        # Filteren op cuisine (keuken)
        if cuisine_filter:
            meal_offerings = [meal for meal in meal_offerings if meal.cuisine == CuisineType[cuisine_filter]]

        # Filteren op stad
        local_meals = [meal for meal in meal_offerings if meal.vendor.Stad == city]  # Lokale maaltijden
        other_meals = [meal for meal in meal_offerings if meal.vendor.Stad != city]  # Andere maaltijden
        meal_offerings_sorted = local_meals + other_meals  # Lokale maaltijden bovenaan

        # Bereken de gemiddelde beoordeling voor maaltijden
        def get_average_rating(meal_id):
            reviews = Review.query.filter_by(meal_id=meal_id).all()
            if reviews:
                total_score = sum(review.score for review in reviews)
                return total_score / len(reviews)
            return 0

        # Sorteer maaltijden op basis van beoordeling
        meal_offerings_sorted = sorted(meal_offerings_sorted, key=lambda meal: get_average_rating(meal.meal_id), reverse=True)

        return render_template('index.html', username=user.username, listings=meal_offerings_sorted)
    else:
        return redirect(url_for('main.login'))  # Als de gebruiker niet is ingelogd, stuur naar loginpagina
