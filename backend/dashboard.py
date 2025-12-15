import requests
import time
from flask import Blueprint, render_template, request
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from flask_login import current_user
bp = Blueprint('dashboard', __name__)
API_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 90  
PER_PAGE = 20   
@bp.route('/dashboard')
def dashboard():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '').strip().lower()
    params = {
        "vs_currency": "inr",
        "order": "market_cap_desc",
        "per_page": 250,  
        "page": 1,
        "sparkline": "true",
        "price_change_percentage": "7d"
    }
    coins = []
    api_error = None
    now = time.time()
    if API_CACHE["data"] and (now - API_CACHE["timestamp"] < CACHE_TTL):
        coins = API_CACHE["data"]
    else:
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                coins = resp.json()
                API_CACHE["data"] = coins
                API_CACHE["timestamp"] = now
            elif resp.status_code == 429:
                api_error = "CoinGecko API rate limit exceeded. Please wait and refresh."
            else:
                api_error = "Failed to fetch market data."
        except Exception as e:
            print("API Error:", e)
            api_error = "Unable to connect to CoinGecko API."
    if search and isinstance(coins, list):
        coins = [
            c for c in coins
            if search in c.get('name', '').lower() or search in c.get('symbol', '').lower()
        ]
    total_coins = len(coins)
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    coins_page = coins[start:end]
    for coin in coins_page:
        sparkline = coin.get('sparkline_in_7d', {})
        prices = sparkline.get('price', []) if isinstance(sparkline, dict) else []
        if not prices:
            prices = [coin.get('current_price', 0)]
        change = coin.get('price_change_percentage_24h') or 0
        fig, ax = plt.subplots(figsize=(1.5, 0.4))
        ax.plot(
            prices,
            color='#21d07a' if change >= 0 else '#ff6b6b',
            linewidth=1.2
        )
        ax.axis('off')
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        coin['sparkline_img'] = base64.b64encode(buf.read()).decode('utf-8')
    next_page = page + 1 if end < total_coins else None
    prev_page = page - 1 if page > 1 else None
    user_name = (
        current_user.name
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated
        else None
    )
    return render_template(
        'dashboard.html',
        coins=coins_page,
        page=page,
        next_page=next_page,
        prev_page=prev_page,
        search=search,
        user_name=user_name,
        api_error=api_error
    )
