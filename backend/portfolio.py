import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, PortfolioItem
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import os
import json
import time
bp = Blueprint('portfolio', __name__)
COINS_CACHE = os.path.join(os.path.dirname(__file__), 'coingecko_coins_cache.json')
CACHE_MAX_AGE = 60 * 60 * 24 
COINGECKO_COINS = []
try:
    cache_exists = os.path.exists(COINS_CACHE)
    cache_fresh = cache_exists and (time.time() - os.path.getmtime(COINS_CACHE) < CACHE_MAX_AGE)
    if cache_fresh:
        with open(COINS_CACHE, 'r') as f:
            COINGECKO_COINS = json.load(f)
        print("[INFO] Loaded CoinGecko coins list from cache.")
    else:
        COINGECKO_COINS = requests.get('https://api.coingecko.com/api/v3/coins/list', timeout=10).json()
        if not isinstance(COINGECKO_COINS, list):
            raise ValueError("CoinGecko API did not return a list")
        with open(COINS_CACHE, 'w') as f:
            json.dump(COINGECKO_COINS, f)
        print("[INFO] Refreshed CoinGecko coins list from API.")
except Exception as e:
    if os.path.exists(COINS_CACHE):
        with open(COINS_CACHE, 'r') as f:
            COINGECKO_COINS = json.load(f)
        print("[WARN] Used stale CoinGecko coins list from cache due to error: ", e)
    else:
        COINGECKO_COINS = []
        print(f"[ERROR] Could not fetch or load CoinGecko coins list: {e}")
SYMBOL_MAP = {c['symbol'].lower(): c['id'] for c in COINGECKO_COINS}
NAME_MAP   = {c['name'].lower(): c['id'] for c in COINGECKO_COINS}
ID_MAP     = {c['id'].lower(): c['id'] for c in COINGECKO_COINS}
def normalize_coin(text):
    t = text.strip().lower()
    if t in ID_MAP:
        return ID_MAP[t]
    if t in SYMBOL_MAP:
        return SYMBOL_MAP[t]
    if t in NAME_MAP:
        return NAME_MAP[t]
    for c in COINGECKO_COINS:
        if t == c['name'].strip().lower().replace(' ', ''):
            return c['id']
        if t in c['name'].strip().lower() or t in c['id'].strip().lower():
            return c['id']
    return None
def fetch_prices_batch(coin_ids):
    if not coin_ids:
        return {}
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': ','.join(coin_ids),
        'vs_currencies': 'inr'
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        missing = [cid for cid in coin_ids if cid not in data or 'inr' not in data.get(cid, {})]
        if missing:
            print(f"[WARN] No INR price for: {missing}")
        return data
    except Exception as e:
        print(f"[ERROR] CoinGecko price fetch failed: {e}")
        return {}
@bp.route('/portfolio', methods=['GET', 'POST'])
@login_required
def portfolio_page():
    if request.method == 'POST':
        coin_input = request.form.get('coinName', '').strip()
        amount = request.form.get('coinAmount', type=float)
        buy_price = request.form.get('buyPrice', type=float)
        if not coin_input or amount is None or buy_price is None:
            flash('All fields are required!', 'error')
            return redirect(url_for('portfolio.portfolio_page'))
        coin_id = normalize_coin(coin_input)
        if not coin_id:
            flash(f'Invalid coin: {coin_input}', 'error')
            return redirect(url_for('portfolio.portfolio_page'))
        item = PortfolioItem(user_id=current_user.id, coin_id=coin_id, qty=amount, buy_price=buy_price)
        db.session.add(item)
        db.session.commit()
        flash(f'{coin_id.upper()} added to portfolio!', 'success')
        return redirect(url_for('portfolio.portfolio_page'))
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return render_template(
            'portfolio.html',
            portfolio=[],
            prices={},
            total_value=0,
            overall_pl=0,
            pie_chart=None,
            bar_chart=None
        )
    portfolio = []
    total_value = overall_pl = 0
    labels = []
    values = []
    coin_ids = [item.coin_id for item in items]
    prices = fetch_prices_batch(coin_ids)
    for item in items:
        price = prices.get(item.coin_id, {}).get('inr')
        if price is None:
            price = 0
            price_na = True
        else:
            price_na = False
        total_val = price * item.qty
        pl = (price - item.buy_price) * item.qty if not price_na else 0
        pl_pct = (100 * (price - item.buy_price) / item.buy_price) if item.buy_price and not price_na else 0
        total_value += total_val
        overall_pl += pl
        labels.append(item.coin_id)
        values.append(total_val)
        portfolio.append({
            'id': item.coin_id,
            'amount': item.qty,
            'buy': item.buy_price,
            'price': price if not price_na else None,
            'price_na': price_na,
            'total_value': total_val if not price_na else None,
            'pl': pl if not price_na else None,
            'pl_pct': pl_pct if not price_na else None,
            'db_id': item.id
        })
    pie_chart = bar_chart = None
    if values and sum(values) > 0:
        fig1, ax1 = plt.subplots(figsize=(4,4))
        ax1.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        buf1 = BytesIO()
        plt.savefig(buf1, format='png', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig1)
        pie_chart = base64.b64encode(buf1.getvalue()).decode('utf-8')
        fig2, ax2 = plt.subplots(figsize=(4,4))
        ax2.bar(labels, values, color='skyblue')
        ax2.set_ylabel('Value (INR)')
        buf2 = BytesIO()
        plt.savefig(buf2, format='png', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig2)
        bar_chart = base64.b64encode(buf2.getvalue()).decode('utf-8')
    return render_template('portfolio.html',
                           portfolio=portfolio,
                           prices=prices,
                           total_value=total_value,
                           overall_pl=overall_pl,
                           pie_chart=pie_chart,
                           bar_chart=bar_chart)
@bp.route('/portfolio/edit/<int:item_id>', methods=['POST'])
@login_required
def edit_coin(item_id):
    item = PortfolioItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        flash('Coin not found.', 'error')
        return redirect(url_for('portfolio.portfolio_page'))
    amount = request.form.get('coinAmount', type=float)
    buy_price = request.form.get('buyPrice', type=float)
    if amount is None or buy_price is None:
        flash('Both amount and buy price are required.', 'error')
        return redirect(url_for('portfolio.portfolio_page'))
    if amount <= 0:
        db.session.delete(item)
    else:
        item.qty = amount
        item.buy_price = buy_price
    db.session.commit()
    flash(f'{item.coin_id.upper()} updated successfully!', 'success')
    return redirect(url_for('portfolio.portfolio_page'))
@bp.route('/portfolio/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_coin(item_id):
    item = PortfolioItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash(f'{item.coin_id.upper()} removed from portfolio.', 'success')
    return redirect(url_for('portfolio.portfolio_page'))
