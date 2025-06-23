from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db
# db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('customer', 'merchant'), default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    points = db.Column(db.Integer, default=0)
    member_level = db.Column(db.String(20), default='普通会员')

    # 关系
    orders = db.relationship('Order', backref='user', lazy='dynamic')
    reviews = db.relationship('Review', backref='user', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    browsing_history = db.relationship('BrowsingHistory', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_merchant(self):
        return self.user_type == 'merchant'