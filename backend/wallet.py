import os
import json
import time
from flask import Blueprint, render_template, request, redirect, url_for
from pycoingecko import CoinGeckoAPI
from flask_login import current_user
from models import db, WalletItem

bp = Blueprint("wallet", __name__, url_prefix="/wallet")
cg = CoinGeckoAPI()

COINS_CACHE = os.path.join(os.path.dirname(__file__), 'coingecko_coins_cache.json')
CACHE_MAX_AGE = 60 * 60 * 24  

try:
    if os.path.exists(COINS_CACHE) and (time.time() - os.path.getmtime(COINS_CACHE)) < CACHE_MAX_AGE:
        with open(COINS_CACHE, 'r') as f:
            all_coins = json.load(f)
    else:
        all_coins = cg.get_coins_list()
        with open(COINS_CACHE, 'w') as f:
            json.dump(all_coins, f)
except Exception:
    all_coins = []

SYMBOL_MAP = {c["symbol"].lower(): c["id"] for c in all_coins}
NAME_MAP   = {c["name"].lower(): c["id"] for c in all_coins}
ID_TO_SYMBOL = {c["id"]: c["symbol"].upper() for c in all_coins}

def normalize_coin(text):
    t = text.strip().lower()

    if t in ["btc", "bitcoin"]:
        return "bitcoin"

    if t in SYMBOL_MAP:
        return SYMBOL_MAP[t]
    if t in NAME_MAP:
        return NAME_MAP[t]

    return None

@bp.route("/", methods=["GET", "POST"])
def wallet_page():
    error = None
    if request.method == "POST" and request.form.get("remove_coin"):
        coin_id = request.form.get("remove_coin")
        WalletItem.query.filter_by(
            user_id=current_user.id,
            coin_id=coin_id
        ).delete()
        db.session.commit()
        return redirect(url_for("wallet.wallet_page"))
    if request.method == "POST":
        coin_input = request.form.get("coin_id", "")
        qty_input = request.form.get("quantity", "")

        coin_id = normalize_coin(coin_input)
        if not coin_id:
            error = "Invalid coin"
            return redirect(url_for("wallet.wallet_page"))

        try:
            qty = float(qty_input)
        except:
            error = "Invalid quantity"
            return redirect(url_for("wallet.wallet_page"))

        item = WalletItem.query.filter_by(
            user_id=current_user.id,
            coin_id=coin_id
        ).first()

        if qty <= 0:
            WalletItem.query.filter_by(
                user_id=current_user.id,
                coin_id=coin_id
            ).delete()
        else:
            if item:
                item.qty = qty
            else:
                db.session.add(
                    WalletItem(
                        user_id=current_user.id,
                        coin_id=coin_id,
                        qty=qty
                    )
                )
        db.session.commit()
        return redirect(url_for("wallet.wallet_page"))
    items = WalletItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return render_template("wallet.html", wallet={}, prices={}, total=0, error=None)

    ids = list({item.coin_id for item in items})

    prices = {}
    try:
        prices = cg.get_price(ids=ids, vs_currencies="inr")
    except Exception:
        prices = {}

    wallet = {}
    total = 0

    for item in items:
        price = prices.get(item.coin_id, {}).get("inr")
        if item.coin_id == "bitcoin" and price and price < 1000:
            price = None

        if price:
            total += price * item.qty

        wallet[ID_TO_SYMBOL.get(item.coin_id, item.coin_id.upper())] = (
            item.qty,
            item.coin_id
        )

    return render_template(
        "wallet.html",
        wallet=wallet,
        prices=prices,
        total=round(total, 2),
        error=error
    )
