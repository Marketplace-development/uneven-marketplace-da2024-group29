from flask import Blueprint, request, redirect, url_for, render_template, session, flash
from .models import db, User, Listing

main = Blueprint('main', __name__)

# Route voor de beschikbare maaltijdenpagina (beschikbaar voor ingelogde gebruikers)
@main.route('/')
def index():
    if 'user_id' in session:  # Controleer of de gebruiker is ingelogd
        user = User.query.get(session['user_id'])  # Haal de ingelogde gebruiker op
        listings = Listing.query.all()  # Haal alle beschikbare maaltijden (advertenties) op
        return render_template('index.html', username=user.username, listings=listings)
    else:
        return redirect(url_for('main.login'))  # Als niet ingelogd, stuur naar loginpagina

# Login route: gebruikers kunnen zich hier aanmelden met hun gebruikersnaam
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()  # Zoek de gebruiker in de database
        if user:
            session['user_id'] = user.id  # Zet de gebruiker in de sessie
            return redirect(url_for('main.index'))  # Redirect naar de indexpagina
        flash("Gebruiker niet gevonden, probeer opnieuw.")  # Toon een foutmelding als de gebruiker niet bestaat
    return render_template('Login_Action.html')  # Toon de loginpagina

# Logout route: gebruiker kan uitloggen
@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Verwijder de gebruiker uit de sessie
    return redirect(url_for('main.login'))  # Na uitloggen, stuur naar de loginpagina

# Add listing route: voor het toevoegen van maaltijden
@main.route('/add-listing', methods=['GET', 'POST'])
def add_listing():
    if 'user_id' not in session:  # Controleer of de gebruiker is ingelogd
        return redirect(url_for('main.login'))  # Als niet ingelogd, stuur naar de loginpagina

    if request.method == 'POST':
        listing_name = request.form['listing_name']
        price = float(request.form['price'])
        new_listing = Listing(listing_name=listing_name, price=price, user_id=session['user_id'])
        db.session.add(new_listing)
        db.session.commit()
        flash("Maaltijd toegevoegd!", "success")  # Bevestiging dat het toegevoegd is
        return redirect(url_for('main.index'))  # Na het toevoegen van een maaltijd, stuur terug naar de maaltijdenpagina

    return render_template('add_listing.html')  # Toon het formulier voor het toevoegen van een maaltijd

# Listings route: toon alle beschikbare maaltijden
@main.route('/listings')
def listings():
    all_listings = Listing.query.all()
    return render_template('listings.html', listings=all_listings)

