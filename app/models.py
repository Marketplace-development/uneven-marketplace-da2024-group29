from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import enum
from datetime import datetime

db = SQLAlchemy()

class MealStatus(enum.Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "Not Available"

class TransactionStatus(enum.Enum): # we doen niet met betalen want geven gratis weg??
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    CONCEPT = "Concept"

class CuisineType(enum.Enum):
    ITALIAN = "Italian"
    BELGIAN = "Belgian"
    ASIAN = "Asian"
    FRENCH = "French"
    MEXICAN = "Mexican"
    SPANISH = "Spanish"
    AMERICAN = "American"
    OTHER = "Other"


class User(db.Model):
    __tablename__ = "Users"                                              # Geeft de Table de naam 'Users', moet zelfde zijn als naam van tabel in supabase
    user_id = db.Column(db.Integer, primary_key=True, unique=True)        # ID
    username = db.Column(db.String(80), unique=True, nullable=False)     # UserName
    email = db.Column(db.String(60), unique=True, nullable=False)        # Mail
    street = db.Column(db.String(100), nullable=False)                   # Straatnaam
    number = db.Column(db.String(10), nullable=False)              # Huisnummer
    zip = db.Column(db.String(20), nullable=False)               # Postcode
    city = db.Column(db.String(50), nullable=False)                      # Stad                   
    type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    
    listings = db.relationship("Listing", backref="user", lazy=True)

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'user' }
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(User):
    __tablename__ = 'Customers'  # Geeft de tabel 'Customers' als naam, moet zelfde zijn als supabase tabel
    customer_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), primary_key=True)  # verwzijen naar User-tabel en heeft dezelfde waarde als UserID
   
 

    __mapper_args__ = {
        'polymorphic_identity': 'customer'
    }

    def __repr__(self):
        return f'<Customer {self.username}>'


class Vendor(User):
    __tablename__ = 'Vendors'
    vendorID = db.Column(db.Integer, db.ForeignKey('Users.user_id'), primary_key=True)  # verwzijen naar User-tabel  @ heeft dezelfde waarde als UserID
    
    __mapper_args__ = {
        'polymorphic_identity': 'vendor'
    }

    def __repr__(self):
        return f'<Vendor {self.username}>'


class MealOffering(db.Model):
    __tablename__ = 'meal_offerings' #naam van supabase tabel
    meal_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    picture = db.Column(db.String(200), nullable=True)  #nog bekijken hoe je foto er in zet want is nu een string
    status = db.Column(db.Enum(MealStatus), default=MealStatus.AVAILABLE) #als status = not available, gwn van de website halen.
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.vendor_id'), nullable=False)
    cuisine = db.Column(db.Enum(CuisineType), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    vendor = db.relationship('Vendor', backref='meal_offerings')
    #categories = db.relationship('Category', secondary='meal_category_association', backref=db.backref('meal_offerings', lazy=True))
    #Deze lijn hierboven nog niet nodig? Want we gebruiken assocation en category nog niet


class Transaction(db.Model):
    __tablename__ = 'transactions'
    transaction_id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.CONCEPT)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.customer_id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.vendor_id'), nullable=False)
    #quantity = db.Column(db.Integer, nullable=False)  Dit mag denk ik weg want ook niet in supabase

    meal = db.relationship('MealOffering', backref='transactions') #bij relationship moet je naar python-klasse verwijzen en bij backref ook en NIET naar de tabelnaam in supabase
    customer = db.relationship('Customer', backref='transactions')
    vendor = db.relationship('Vendor', backref='transactions')  

    def validate_transaction(self):
        if self.meal.vendor_id != self.vendor_id:
            raise ValueError("Meal does not belong to the specified vendor.")


# deze klasse hoort er ook niet bij denk ik
# maar er moet in de supabase denk ik wel nog een klasse aangemaakt worden met Meals, waar alle maaltijden die beschikbaar zijn inzitten
class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)      #Mag dit niet weg? We werken toch niet met prijs?
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.listing_name}, ${self.price}>'
    
class Review(db.Model):
    __tablename__ = 'reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.customer_id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.vendor_id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meal = db.relationship('MealOffering', backref='reviews')
    customer = db.relationship('Customer', backref='reviews')
    vendor = db.relationship('Vendor', backref='reviews')


    




# ik denk dat die Category klasse weg mag, want niet in supabase.
#class Category(db.Model):    #onduidelijk wat dit is (paarse blok in ontology)??
    #__tablename__ = 'Categories'
    #category_id = db.Column(db.Integer, primary_key=True)
    #name = db.Column(db.String(50), nullable=False, unique=False)

    #meals = db.relationship('MealOffering', secondary='meal_category_association', backref='categories')



# deze drie lijnen zijn er als je bv wilt dat een maaltijd 2 categorieën heeft zoals spaans en frans
#meal_category_association = db.Table('meal_category_association',
#   db.Column('meal_id', db.Integer, db.ForeignKey('meal_offerings.meal_id', ondelete='CASCADE')),
#    db.Column('category_id', db.Integer, db.ForeignKey('categories.category_id', ondelete='CASCADE')))


    
