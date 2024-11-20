from flask_sqlalchemy import SQLAlchemy
import enum
db = SQLAlchemy()

class MaaltijdStatus(enum.Enum):
    BESCHIKBAAR = "Beschikbaar"
    NIET_BESCHIKBAAR = "Niet Beschikbaar"

class TransactieStatus(enum.Enum): # we doen niet met betalen want geven gratis weg
    VOLTOOID = "Voltooid"
    GEANNULEERD = "Geannuleerd"
    CONCEPT = "Concept"

class CuisineType(enum.Enum):
    ITALIAANS = "Italiaans"
    BELGISCH = "Belgisch"
    AZIATISCH = "Aziatisch"
    FRANS = "Frans"
    MEXICAANS = "Mexicaans"
    SPAANS = "Spaans"
    AMERIKAANS = "Amerikaans"
    ANDERE = "Andere"


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
# geen land, want enkel operationeel in België

    type = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'user' }
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(User):
    __tablename__ = 'Customers'  # Geeft de tabel 'Customers' als naam
    id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)  # verwzijen naar User-tabel en heeft dezelfde waarde als UserID
    CustomerID = db.Column(db.Integer, unique=True, autoincrement=True, nullable=False) # niet zeker of ik een aparte customerID moet maken of enkel Id genoeg is (die we kunnen hernoemen naar CutomerID)
    

    __mapper_args__ = {
        'polymorphic_identity': 'customer'
    }

    def __repr__(self):
        return f'<Customer {self.username}>'


class Vendor(User):
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)  # verwzijen naar User-tabel  @ heeft dezelfde waarde als UserID
    VendorID = db.Column(db.Integer, unique=True, autoincrement=True, nullable=False) 
    
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
    status = db.Column(db.Enum(MealStatus), default=MealStatus.NOT_AVAILABLE) #als status = not available, gwn van de website halen.
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    cuisine = db.Column(db.Enum(CuisineType), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    vendor = db.relationship('Vendor', backref='meal_offerings')
    categories = db.relationship('Category', secondary='meal_category_association', back_populates='meals')



class Category(db.Model):    #onduidelijk wat dit is (paarse blok in ontology)??
    __tablename__ = 'Categories'
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False)

    meals = db.relationship('MealOffering', secondary='meal_category_association', back_populates='categories')

class Transaction(db.Model):
    __tablename__ = 'transactions'
    transaction_id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.DRAFT)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    meal = db.relationship('MealOffering', backref='transactions')
    customer = db.relationship('Customer', backref='transactions')





meal_category_association = db.Table('meal_category_association',
    db.Column('meal_id', db.Integer, db.ForeignKey('meal_offerings.meal_id')),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.category_id'))
)



    

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.listing_name}, ${self.price}>'
    
