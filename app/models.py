from flask_sqlalchemy import SQLAlchemy
import enum
from datetime import datetime

db = SQLAlchemy()

class MaaltijdStatus(enum.Enum):
    BESCHIKBAAR = "Beschikbaar"
    NIET_BESCHIKBAAR = "Niet Beschikbaar"

class TransactieStatus(enum.Enum): # we doen niet met betalen want geven gratis weg
    VOLTOOID = "Voltooid"
    GEANNULEERD = "Geannuleerd"
    CONCEPT = "Concept"

class CuisineType(enum.Enum):
    ITALIAANS = "Italian"
    BELGISCH = "Belgian"
    AZIATISCH = "Asian"
    FRANS = "French"
    MEXICAANS = "Mexican"
    SPAANS = "Spanish"
    AMERIKAANS = "American"
    ANDERE = "Other"


class User(db.Model):
    __tablename__ = 'Users'                                              # Geeft de Table de naam 'Users'
    UserID = db.Column(db.Integer, primary_key=True, unique=True)                     # ID
    username = db.Column(db.String(80), unique=True, nullable=False)     # UserName
    Email = db.Column(db.String(60), unique=True, nullable=False)        # Mail
    Straat = db.Column(db.String(100), nullable=False)                   # Straatnaam
    Huisnummer = db.Column(db.String(10), nullable=False)                # Huisnummer
    Postcode = db.Column(db.String(20), nullable=False)                  # Postcode
    Stad = db.Column(db.String(50), nullable=False)                      # Stad                   
    listings = db.relationship('Listing', backref='user', lazy=True)

    type = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'user' }
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(User):
    __tablename__ = 'Customers'  # Geeft de tabel 'Customers' als naam
    CustomerID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)  # verwzijen naar User-tabel en heeft dezelfde waarde als UserID
   
 

    __mapper_args__ = {
        'polymorphic_identity': 'customer'
    }

    def __repr__(self):
        return f'<Customer {self.username}>'


class Vendor(User):
    __tablename__ = 'Vendors'
    VendorID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)  # verwzijen naar User-tabel  @ heeft dezelfde waarde als UserID
    
    __mapper_args__ = {
        'polymorphic_identity': 'vendor'
    }

    def __repr__(self):
        return f'<Vendor {self.username}>'


class MealOffering(db.Model):
    __tablename__ = 'Meal_Offerings'
    meal_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    picture = db.Column(db.String(200), nullable=True)  #nog bekijken hoe je foto er in zet
    status = db.Column(db.Enum(MaaltijdStatus), default=MaaltijdStatus.BESCHIKBAAR) #als status = not available, gwn van de website halen.
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.VendorID'), nullable=False)
    cuisine = db.Column(db.Enum(CuisineType), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    vendor = db.relationship('Vendor', backref='meal_offerings')
    categories = db.relationship('Category', secondary='meal_category_association', backref=db.backref('meal_offerings', lazy=True))




class Category(db.Model):    #onduidelijk wat dit is (paarse blok in ontology)??
    __tablename__ = 'Categories'
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False)

    meals = db.relationship('MealOffering', secondary='meal_category_association', backref='categories')

class Transaction(db.Model):
    __tablename__ = 'transactions'
    transaction_id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(TransactieStatus), default=TransactieStatus.CONCEPT)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.CustomerID'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.VendorID'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    meal = db.relationship('MealOffering', backref='transactions')
    customer = db.relationship('Customer', backref='transactions')
    vendor = db.relationship('Vendor', backref='transactions')  

    def validate_transaction(self):
        if self.meal.vendor_id != self.vendor_id:
            raise ValueError("Meal does not belong to the specified vendor.")



meal_category_association = db.Table('meal_category_association',
    db.Column('meal_id', db.Integer, db.ForeignKey('meal_offerings.meal_id', ondelete='CASCADE')),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.category_id', ondelete='CASCADE'))
)


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.listing_name}, ${self.price}>'
    
class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.CustomerID'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.VendorID'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meal = db.relationship('MealOffering', backref='reviews')
    customer = db.relationship('Customer', backref='reviews')
    vendor = db.relationship('Vendor', backref='reviews')


    



    
