import os
import requests
import base64
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from flask import (
    Flask, request, jsonify, send_file,
    render_template, redirect, url_for
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from flask_cors import CORS
from models import db, User, PortfolioItem
from dashboard import bp as dashboard_bp
from portfolio import bp as portfolio_bp
from cipher import bp as cipher_bp
from auth import bp as auth_bp
from recommend import bp as recommend_bp
from wallet import bp as wallet_bp
from assets import bp as assets_bp
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "super-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
CORS(app, supports_credentials=True)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.home"
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
@app.route("/")
@app.route("/index.html")
def home():
    return render_template("index.html")
@app.route("/assets", methods=["GET"])
@login_required
def assets_page():
    return render_template(
        "assets.html",
        error=None,
        final_value=None,
        gain=None,
        years=None,
        graph_url=None,
        request=request
    )
@app.post("/api/register")
def api_register():
    data = request.get_json() or {}
    username = data.get("username", "").lower().strip()
    password = data.get("password", "")
    name = data.get("name", "")
    email = data.get("email", "")
    if not username or len(password) < 6:
        return jsonify({"ok": False, "error": "Username & password required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"ok": False, "error": "Username exists"}), 400
    user = User(username=username, name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"ok": True, "msg": "Account created"})
@app.post("/api/login")
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "").lower().strip()
    password = data.get("password", "")
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401
    login_user(user)
    return jsonify({"ok": True, "msg": "Logged in"})
@app.post("/api/logout")
@login_required
def api_logout():
    logout_user()
    return jsonify({"ok": True})
@app.get("/api/whoami")
def whoami():
    if not current_user.is_authenticated:
        return jsonify({"user": None})
    return jsonify({
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email
        }
    })
@app.get("/api/portfolio")
@login_required
def get_portfolio():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            "id": i.id,
            "coin_id": i.coin_id,
            "qty": i.qty,
            "buy_price": i.buy_price
        } for i in items
    ])
@app.post("/api/portfolio")
@login_required
def add_portfolio():
    data = request.get_json() or {}
    coin_id = data.get("coin_id", "").lower()
    qty = float(data.get("qty", 0))
    buy_price = float(data.get("buy_price", 0))
    if not coin_id or qty <= 0:
        return jsonify({"error": "Invalid input"}), 400
    item = PortfolioItem(
        user_id=current_user.id,
        coin_id=coin_id,
        qty=qty,
        buy_price=buy_price
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"ok": True})
@app.get("/api/portfolio/export/csv")
@login_required
def export_csv():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{
        "coin": i.coin_id,
        "qty": i.qty,
        "buy_price": i.buy_price
    } for i in items])
    bio = BytesIO()
    df.to_csv(bio, index=False)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name="portfolio.csv")
app.register_blueprint(dashboard_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(cipher_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(recommend_bp)
app.register_blueprint(assets_bp) 
app.register_blueprint(wallet_bp)
if __name__ == "__main__":
    with app.app_context():
        if not os.path.exists("app.db"):
            db.create_all()
    app.run(debug=True, host="127.0.0.1", port=8000)
