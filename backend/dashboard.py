import requests
from flask import Blueprint, render_template, current_app, send_file, request
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from flask_login import current_user

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
def dashboard():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    page = int(request.args.get('page', 1))
    per_page = 20
    params = {
        "vs_currency": "inr",
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
        "sparkline": "true"
    }
    search = request.args.get('search', '').strip().lower()
    try:
        resp = requests.get(url, params=params, timeout=10)
        coins = resp.json()
    except Exception as e:
        coins = []
    import json
    parsed_coins = []
    for coin in coins:
        if isinstance(coin, str):
            try:
                coin = json.loads(coin)
            except Exception:
                continue  
        if isinstance(coin, dict):
            parsed_coins.append(coin)
    coins = parsed_coins
    if search:
        coins = [c for c in coins if search in c.get('name','').lower() or search in c.get('symbol','').lower()]
    for coin in coins:
        prices = coin.get('sparkline_in_7d', {}).get('price', [coin.get('current_price', 0)])
        fig, ax = plt.subplots(figsize=(1.5, 0.4))
        ax.plot(prices, color='#21d07a' if coin.get('price_change_percentage_24h', 0) >= 0 else '#ff6b6b', linewidth=1.2)
        ax.axis('off')
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        coin['sparkline_img'] = base64.b64encode(buf.read()).decode('utf-8')
    next_page = page + 1
    prev_page = page - 1 if page > 1 else None
    user_name = None
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        user_name = getattr(current_user, 'name', None)
    api_error = None
    if isinstance(coins, list) and coins and isinstance(coins[0], dict) and 'status' in coins[0]:
        status = coins[0]['status']
        if status.get('error_code') == 429:
            api_error = 'CoinGecko API rate limit exceeded. Please wait a few minutes and try again.'
    elif isinstance(coins, dict) and 'status' in coins:
        status = coins['status']
        if status.get('error_code') == 429:
            api_error = 'CoinGecko API rate limit exceeded. Please wait a few minutes and try again.'
    return render_template('dashboard.html', coins=coins, page=page, next_page=next_page, prev_page=prev_page, search=search, user_name=user_name, api_error=api_error)
