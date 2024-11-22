# app/routes.py


from flask import Blueprint, request, redirect, url_for, render_template, session
from .models import db, User, Listing

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        listings = Listing.query.filter_by(user_id=user.id).all()  # Fetch listings for logged-in user
        return render_template('index.html', username=user.username, listings=listings)
    return render_template('index.html', username=None)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first() is None:
            new_user = User(username=username)
            db.session.add(new_user)
            db.session.commit()
            session['user_id'] = new_user.id
            return redirect(url_for('main.index'))
        return 'Username already registered'
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('main.index'))
        return 'User not found'
    return render_template('login.html')

@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))

@main.route('/add-listing', methods=['GET', 'POST'])
def add_listing():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        listing_name = request.form['listing_name']
        price = float(request.form['price'])
        new_listing = Listing(listing_name=listing_name, price=price, user_id=session['user_id'])
        db.session.add(new_listing)
        db.session.commit()
        return redirect(url_for('main.listings'))

    return render_template('add_listing.html')

@main.route('/listings')
def listings():
    all_listings = Listing.query.all()
    return render_template('listings.html', listings=all_listings)



def index():
    try:
        # Test databaseverbinding door een eenvoudige query uit te voeren
        db.engine.execute("SELECT 1")
        return "Verbinding succesvol met de database!", 200
    except Exception as e:
        return f"Fout bij verbinding maken met de database: {str(e)}", 500