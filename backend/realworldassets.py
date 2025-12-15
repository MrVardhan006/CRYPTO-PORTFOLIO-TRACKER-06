import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, RealWorldAsset
import os
import json
import time
import matplotlib.pyplot as plt
from io import BytesIO
import base64

bp = Blueprint("realworldassets", __name__, url_prefix="/realworldassets")

# Cache configuration
COINS_CACHE = os.path.join(os.path.dirname(__file__), "coingecko_coins_cache.json")
CACHE_MAX_AGE = 60 * 60 * 24  # 24 hours
COINGECKO_COINS = []

# Load or fetch CoinGecko coins
try:
    cache_exists = os.path.exists(COINS_CACHE)
    cache_fresh = cache_exists and (time.time() - os.path.getmtime(COINS_CACHE) < CACHE_MAX_AGE)
    if cache_fresh:
        with open(COINS_CACHE, "r") as f:
            COINGECKO_COINS = json.load(f)
        print("[INFO] Loaded CoinGecko coins list from cache.")
    else:
        COINGECKO_COINS = requests.get("https://api.coingecko.com/api/v3/coins/list", timeout=10).json()
        with open(COINS_CACHE, "w") as f:
            json.dump(COINGECKO_COINS, f)
        print("[INFO] Refreshed CoinGecko coins list from API.")
except Exception as e:
    if os.path.exists(COINS_CACHE):
        with open(COINS_CACHE, "r") as f:
            COINGECKO_COINS = json.load(f)
        print("[WARN] Used stale CoinGecko coins list due to error:", e)
    else:
        COINGECKO_COINS = []
        print(f"[ERROR] Could not fetch or load CoinGecko coins list: {e}")

# Maps for lookup
SYMBOL_MAP = {c["symbol"].lower(): c["id"] for c in COINGECKO_COINS}
NAME_MAP = {c["name"].lower(): c["id"] for c in COINGECKO_COINS}
ID_MAP = {c["id"].lower(): c["id"] for c in COINGECKO_COINS}


def normalize_coin(text):
    t = text.strip().lower()
    if t in ID_MAP:
        return ID_MAP[t]
    if t in SYMBOL_MAP:
        return SYMBOL_MAP[t]
    if t in NAME_MAP:
        return NAME_MAP[t]
    # fallback: partial match
    for c in COINGECKO_COINS:
        if t.replace(" ", "") == c["name"].lower().replace(" ", ""):
            return c["id"]
        if t in c["name"].lower() or t in c["id"].lower():
            return c["id"]
    return None


def fetch_prices_batch(coin_ids):
    if not coin_ids:
        return {}
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(coin_ids), "vs_currencies": "inr"}
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.json()
    except Exception as e:
        print("[ERROR] CoinGecko price fetch failed:", e)
        return {}


@bp.route("/", methods=["GET", "POST"])
@login_required
def realworldassets_page():
    if request.method == "POST":
        name = request.form.get("name").strip()
        coin_input = request.form.get("coin_id").strip()
        quantity = request.form.get("quantity", type=float)

        if not name or not coin_input or quantity is None:
            flash("All fields are required!", "error")
            return redirect(url_for("realworldassets.realworldassets_page"))

        coin_id = normalize_coin(coin_input)
        if not coin_id:
            flash(f"Coin '{coin_input}' not recognized. Use CoinGecko ID, symbol, or name.", "error")
            return redirect(url_for("realworldassets.realworldassets_page"))

        asset = RealWorldAsset(user_id=current_user.id, name=name, coin_id=coin_id, quantity=quantity)
        db.session.add(asset)
        db.session.commit()

        flash(f"{name} ({coin_id}) added successfully!", "success")
        return redirect(url_for("realworldassets.realworldassets_page"))

    # GET request: show assets
    assets = RealWorldAsset.query.filter_by(user_id=current_user.id).all()
    coin_ids = [a.coin_id for a in assets]
    prices = fetch_prices_batch(coin_ids)

    asset_data = []
    total_value = 0
    labels = []
    values = []

    for asset in assets:
        price = prices.get(asset.coin_id, {}).get("inr", 0)
        value = asset.quantity * price
        total_value += value
        asset_data.append({
            "id": asset.id,
            "name": asset.name,
            "quantity": asset.quantity,
            "price": price,
            "value": value
        })
        labels.append(asset.name)
        values.append(value)

    # Generate pie chart
    pie_chart = bar_chart = None
    if values and sum(values) > 0:
        plt.figure(figsize=(4, 4))
        plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1)
        plt.close()
        pie_chart = base64.b64encode(buf.getvalue()).decode("utf-8")

        # Bar chart
        plt.figure(figsize=(5, 4))
        plt.bar(labels, values, color="skyblue")
        plt.ylabel("Value (INR)")
        buf2 = BytesIO()
        plt.savefig(buf2, format="png", bbox_inches="tight", pad_inches=0.1)
        plt.close()
        bar_chart = base64.b64encode(buf2.getvalue()).decode("utf-8")

    return render_template(
        "realworldassets.html",
        assets=asset_data,
        total_value=total_value,
        pie_chart=pie_chart,
        bar_chart=bar_chart
    )


@bp.route("/delete/<int:asset_id>")
@login_required
def delete_realworldasset(asset_id):
    asset = RealWorldAsset.query.get_or_404(asset_id)
    if asset.user_id != current_user.id:
        flash("Unauthorized action.", "error")
        return redirect(url_for("realworldassets.realworldassets_page"))
    db.session.delete(asset)
    db.session.commit()
    flash("Asset removed successfully.", "success")
    return redirect(url_for("realworldassets.realworldassets_page"))
