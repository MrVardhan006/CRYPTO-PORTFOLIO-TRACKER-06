from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(200))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    coin_id = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Float, default=0)
    buy_price = db.Column(db.Float, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="portfolio_items")

class WalletItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    coin_id = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Float, default=0)
    buy_price = db.Column(db.Float, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    wallet_name = db.Column(db.String(120), default="Default Wallet")
    wallet_id = db.Column(db.Integer, default=1)
    user = db.relationship("User", backref="wallet_items")
