import os
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from datetime import datetime
from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt
import base64
import matplotlib
matplotlib.use('Agg')
from dashboard import bp as dashboard_bp
from portfolio import bp as portfolio_bp
from cipher import bp as cipher_bp
from auth import bp as auth_bp
from models import db, User, PortfolioItem
from recommend import bp as recommend_bp
from wallet import bp as wallet_bp

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

CORS(app, supports_credentials=True)

login_manager = LoginManager(app)
login_manager.login_view = "home"
login_manager.session_protection = "strong"

COINGECKO = "https://api.coingecko.com/api/v3"


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


@app.route("/")
@app.route("/index.html")
def home():
    return render_template("index.html")




@app.route("/assets", methods=["GET"])
@login_required
def assets_page():
    return render_template("assets.html", error=None, final_value=None, gain=None, years=None, graph_url=None, request=request)


@app.post("/api/register")
def api_register():
    data = request.get_json() or {}
    name = data.get("name") or ""
    username = (data.get("username") or "").lower().strip()
    email = data.get("email") or ""
    password = data.get("password") or ""
    if not username or len(password) < 6:
        return jsonify({"ok": False, "error": "Username & password (min 6 chars) required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"ok": False, "error": "Username already exists"}), 400
    user = User(name=name, username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"ok": True, "msg": "Account created"})


@app.post("/api/login")
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").lower().strip()
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"ok": False, "error": "Invalid username or password"}), 401
    login_user(user)
    return jsonify({"ok": True, "msg": "Logged in", "user": {"id": user.id, "username": user.username, "email": user.email}})


@app.post("/api/logout")
@login_required
def api_logout():
    logout_user()
    return jsonify({"ok": True, "msg": "Logged out"})


@app.get("/api/whoami")
def api_whoami():
    if not current_user.is_authenticated:
        return jsonify({"ok": True, "user": None})
    return jsonify({"ok": True, "user": {"id": current_user.id, "username": current_user.username, "email": current_user.email}})


@app.get("/api/portfolio")
@login_required
def api_get_portfolio():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    return jsonify({"ok": True, "portfolio": [{"id": i.id, "coin_id": i.coin_id, "qty": i.qty, "buy_price": i.buy_price, "added_at": i.added_at.isoformat()} for i in items]})


@app.post("/api/portfolio")
@login_required
def api_add_portfolio_item():
    data = request.get_json() or {}
    coin_id = (data.get("coin_id") or "").lower().strip()
    try:
        qty = float(data.get("qty", 0))
        buy_price = float(data.get("buy_price", 0))
    except Exception:
        return jsonify({"ok": False, "error": "Invalid numeric values"}), 400
    if not coin_id or qty <= 0:
        return jsonify({"ok": False, "error": "coin_id + qty required"}), 400
    existing = PortfolioItem.query.filter_by(user_id=current_user.id, coin_id=coin_id).first()
    if existing:
        total_qty = existing.qty + qty
        existing.buy_price = ((existing.buy_price * existing.qty) + (buy_price * qty)) / total_qty
        existing.qty = total_qty
        db.session.commit()
        return jsonify({"ok": True, "msg": "Item updated"})
    new_item = PortfolioItem(user_id=current_user.id, coin_id=coin_id, qty=qty, buy_price=buy_price)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({"ok": True, "msg": "Item added"})


@app.delete("/api/portfolio/<int:item_id>")
@login_required
def api_delete_portfolio_item(item_id):
    item = PortfolioItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"ok": False, "error": "Not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True, "msg": "Deleted"})


@app.get("/api/markets")
def api_markets():
    try:
        params = {
            "vs_currency": request.args.get("vs_currency", "inr"),
            "order": request.args.get("order", "market_cap_desc"),
            "per_page": request.args.get("per_page", "100"),
            "page": request.args.get("page", "1"),
            "sparkline": request.args.get("sparkline", "true")
        }
        resp = requests.get(COINGECKO + "/coins/markets", params=params, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/simple-price")
def api_simple_price():
    ids = request.args.get("ids", "")
    try:
        resp = requests.get(COINGECKO + "/simple/price", params={"ids": ids, "vs_currencies": "inr"}, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/portfolio/export/csv")
@login_required
def export_csv():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{"coin_id": i.coin_id, "qty": i.qty, "buy_price": i.buy_price, "added_at": i.added_at} for i in items])
    bio = BytesIO()
    df.to_csv(bio, index=False)
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name="portfolio.csv")


@app.get("/api/portfolio/export/xlsx")
@login_required
def export_xlsx():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([{"coin_id": i.coin_id, "qty": i.qty, "buy_price": i.buy_price, "added_at": i.added_at} for i in items])
    bio = BytesIO()
    df.to_excel(bio, index=False, engine="xlsxwriter")
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name="portfolio.xlsx")


@app.route("/total_assets", methods=["POST"])
@login_required
def total_assets():
    initial_investment = request.form.get("initial_investment", type=float)
    years = request.form.get("years", type=int)
    assets = request.form.getlist("assets")
    allocations = {}
    returns = {}
    for asset in ["Stocks", "Bonds", "Mutual Funds", "Gold", "Cash"]:
        allocations[asset] = request.form.get(f"allocation_{asset.replace(' ', '')}", type=float) or 0
        returns[asset] = request.form.get(f"return_{asset.replace(' ', '')}", type=float) or 0
    if not assets:
        return render_template("assets.html", error="Please select at least one asset.")
    if sum([allocations[a] for a in assets]) != 100:
        return render_template("assets.html", error="Total allocation must be 100%.")
    yearly_values = {asset: [] for asset in assets}
    for year in range(years + 1):
        for asset in assets:
            alloc_amount = initial_investment * (allocations[asset] / 100)
            rate = returns[asset] / 100
            value = alloc_amount * ((1 + rate) ** year)
            yearly_values[asset].append(value)
    plt.figure(figsize=(7,4))  
    x = list(range(years + 1))
    y = [yearly_values[asset] for asset in assets]
    plt.stackplot(x, *y, labels=assets)
    plt.title(f"Portfolio Growth Over {years} Years")
    plt.xlabel("Year")
    plt.ylabel("Portfolio Value (₹)")
    plt.legend(loc="upper left")
    plt.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.6)
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    graph_url = base64.b64encode(buf.getvalue()).decode("utf-8")
    final_value = sum([yearly_values[asset][-1] for asset in assets])
    gain = final_value - initial_investment
    return render_template(
        "assets.html",final_value=final_value,gain=gain,years=years,error=None,
        graph_url=graph_url,request=request
    )


if __name__ == "__main__":
    with app.app_context():
        db.init_app(app)
        if not os.path.exists("app.db"):
            db.create_all()
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(cipher_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(wallet_bp)
    app.run(debug=True, host="127.0.0.1", port=8000)
