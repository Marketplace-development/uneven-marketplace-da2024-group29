from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'Users'                                              # Geeft de Table de naam 'Users'
    UserID = db.Column(db.Integer, primary_key=True)                     # ID
    username = db.Column(db.String(80), unique=True, nullable=False)     # UserName
    Email = db.Column(db.String(60), unique=True, nullable=False)        # Mail
    Straat = db.Column(db.String(100), nullable=False)                   # Straatnaam
    Huisnummer = db.Column(db.String(10), nullable=False)                # Huisnummer
    Postcode = db.Column(db.String(20), nullable=False)                  # Postcode
    Stad = db.Column(db.String(50), nullable=False)                      # Stad
    Land = db.Column(db.String(50), nullable=False)                      # Land // Niet persee nodig omdat onze website alleen in Belgie is?? //
    listings = db.relationship('Listing', backref='user', lazy=True)


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
    

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.listing_name}, ${self.price}>'
    
