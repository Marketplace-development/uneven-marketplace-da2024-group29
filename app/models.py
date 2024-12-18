from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, Float, Date, Time
from enum import Enum
from datetime import datetime

db = SQLAlchemy()


class CuisineType(Enum):
    ITALIAN = "Italian"
    BELGIAN = "Belgian"
    ASIAN = "Asian"
    FRENCH = "French"
    MEXICAN = "Mexican"
    SPANISH = "Spanish"
    AMERICAN = "American"
    OTHER = "Other"


class MealStatus(Enum):
    AVAILABLE = "AVAILABLE"
    CLAIMED = "CLAIMED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"


class User(db.Model):
    __tablename__ = "Users"                                              
    user_id = db.Column(db.Integer, primary_key=True, unique=True)     
    username = db.Column(db.String(80), unique=True, nullable=False)     
    email = db.Column(db.String(60), unique=True, nullable=False)    
    street = db.Column(db.String(100), nullable=False)                   
    number = db.Column(db.String(10), nullable=False)             
    zip = db.Column(db.String(20), nullable=False)            
    city = db.Column(db.String(50), nullable=False)                                 
    type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    latitude = db.Column(Float, nullable=True)                     
    longitude = db.Column(Float, nullable=True)                     
    
    listings = db.relationship("Listing", backref="user", lazy=True)

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'user' } 
    
    def __repr__(self):
        return f'<User {self.username}>'


class Customer(db.Model):
    __tablename__ = 'Customers'  
    customer_id = db.Column(db.Integer, primary_key=True) 
    amount = db.Column(db.Integer, nullable = False)
 

    __mapper_args__ = {
        'polymorphic_identity': 'customer'
    }

    def __repr__(self):
        return f'<Customer {self.username}>'


class Vendor(db.Model):
    __tablename__ = 'Vendors'
    vendor_id = db.Column(db.Integer, primary_key=True)  
    average_rating = db.Column(db.Float, default=0.0)
    __mapper_args__ = {
        'polymorphic_identity': 'vendor' 
    }

    def __repr__(self):
        return f'<Vendor {self.vendor_id}>'


class Meal_offerings(db.Model):
    __tablename__ = 'Meal_offerings' 
    meal_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    picture = db.Column(db.String(200), nullable=True) 
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.vendor_id'), nullable=False)
    cuisine = db.Column(db.Enum(CuisineType), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(MealStatus), nullable=False, default=MealStatus.AVAILABLE)
    pickup_date = db.Column(Date, nullable=True)
    pickup_start_time = db.Column(Time, nullable=True)
    pickup_end_time = db.Column(Time, nullable=True)
    vendor = db.relationship('Vendor', backref='Meal_offerings')
    deleted_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def mark_as_expired(self):
        now = datetime.utcnow().date()
        current_time = datetime.utcnow().time()

        print(f"DEBUG - Current Date: {now}, Current Time: {current_time}")
        print(f"DEBUG - Pickup Date: {self.pickup_date}, Pickup End Time: {self.pickup_end_time}")

        if self.pickup_date:
            if self.pickup_date < now:
                self.status = MealStatus.EXPIRED
            elif self.pickup_date == now and self.pickup_end_time and self.pickup_end_time < current_time:
                self.status = MealStatus.EXPIRED
    

class Transaction(db.Model):
    __tablename__ = 'Transactions'
    transaction_id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('Meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.customer_id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.vendor_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meal = db.relationship('Meal_offerings', backref='transactions')
    customer = db.relationship('Customer', backref='transactions')
    vendor = db.relationship('Vendor', backref='transactions')  
    
    def validate_transaction(self):
        if self.meal.vendor_id != self.vendor_id:
            raise ValueError("Meal does not belong to the specified vendor.")


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False)

    def __repr__(self):
        return f'<Listing {self.listing_name}, ${self.price}>'
    

class Review(db.Model):
    __tablename__ = 'Reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('Meal_offerings.meal_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.customer_id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('Vendors.vendor_id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meal = db.relationship('Meal_offerings', backref='reviews')
    customer = db.relationship('Customer', backref='reviews')
    vendor = db.relationship('Vendor', backref='reviews')
