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
CACHE_MAX_AGE = 60 * 60 * 24  # 24 hours
all_coins = []
try:
    cache_exists = os.path.exists(COINS_CACHE)
    cache_fresh = cache_exists and (time.time() - os.path.getmtime(COINS_CACHE) < CACHE_MAX_AGE)
    if cache_fresh:
        with open(COINS_CACHE, 'r') as f:
            all_coins = json.load(f)
        print("[INFO] Loaded CoinGecko coins list from cache.")
    else:
        all_coins = cg.get_coins_list()
        if not isinstance(all_coins, list):
            raise ValueError("CoinGecko API did not return a list")
        with open(COINS_CACHE, 'w') as f:
            json.dump(all_coins, f)
        print("[INFO] Refreshed CoinGecko coins list from API.")
except Exception as e:
    if os.path.exists(COINS_CACHE):
        with open(COINS_CACHE, 'r') as f:
            all_coins = json.load(f)
        print("[WARN] Used stale CoinGecko coins list from cache due to error: ", e)
    else:
        all_coins = []
        print(f"[ERROR] Could not fetch or load CoinGecko coins list: {e}")

SYMBOL_MAP = {c["symbol"].lower(): c["id"] for c in all_coins}
NAME_MAP   = {c["name"].lower():   c["id"] for c in all_coins}
ID_TO_SYMBOL = {c["id"]: c["symbol"].upper() for c in all_coins}

def normalize_coin(text):
    t = text.strip().lower()
    if t in ID_TO_SYMBOL:
        return t
    if t in SYMBOL_MAP:
        return SYMBOL_MAP[t]
    if t in NAME_MAP:
        return NAME_MAP[t]
    for c in all_coins:
        if t == c['name'].strip().lower().replace(' ', ''):
            return c['id']
        if t in c['name'].strip().lower() or t in c['id'].strip().lower():
            return c['id']
    return None

@bp.route("/", methods=["GET", "POST"])
def wallet_page():
    error = None
    if request.method == "POST":
        remove_coin = request.form.get("remove_coin")
        if remove_coin:
            cid = None
            if remove_coin.lower() in SYMBOL_MAP:
                cid = SYMBOL_MAP[remove_coin.lower()]
            elif remove_coin.lower() in ID_TO_SYMBOL:
                cid = remove_coin.lower()
            else:
                # Try to normalize
                cid = normalize_coin(remove_coin)
            if cid:
                WalletItem.query.filter_by(user_id=current_user.id, coin_id=cid).delete()
                db.session.commit()
            return redirect(url_for("wallet.wallet_page"))
        coin_input = request.form.get("coin_id", "")
        quantity = request.form.get("quantity", "")
        coin_id = normalize_coin(coin_input)
        if not coin_id:
            error = f"Invalid coin: {coin_input}"
            return render_template(
                "wallet.html",
                wallet={},
                prices={},
                total=0,
                error=error
            )
        try:
            qty = float(quantity)
        except Exception:
            error = "Invalid quantity."
            return render_template(
                "wallet.html",
                wallet={},
                prices={},
                total=0,
                error=error
            )
        if qty <= 0:
            WalletItem.query.filter_by(user_id=current_user.id, coin_id=coin_id).delete()
        else:
            item = WalletItem.query.filter_by(user_id=current_user.id, coin_id=coin_id).first()
            if item:
                item.qty = qty
            else:
                item = WalletItem(user_id=current_user.id, coin_id=coin_id, qty=qty)
                db.session.add(item)
        db.session.commit()
        return redirect(url_for("wallet.wallet_page"))
    items = WalletItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return render_template(
            "wallet.html",
            wallet={},
            prices={},
            total=0,
            error=error
        )
    ids = [item.coin_id for item in items]
    prices = {}
    if ids:
        try:
            prices = cg.get_price(ids=','.join(ids), vs_currencies='inr')
            missing = [cid for cid in ids if cid not in prices or 'inr' not in prices.get(cid, {})]
            if missing:
                print(f"[WARN] No INR price for: {missing}")
        except Exception as e:
            print(f"[ERROR] CoinGecko price fetch failed: {e}")
            prices = {}
    display_wallet = {ID_TO_SYMBOL.get(item.coin_id, item.coin_id.upper()): (item.qty, item.coin_id) for item in items}
    total_value = 0
    for symbol, (qty, cid) in display_wallet.items():
        price = prices.get(cid, {}).get('inr')
        if price is not None:
            total_value += price * qty
    return render_template(
        "wallet.html",
        wallet=display_wallet,
        prices=prices,
        total=total_value,
        error=error
    )
