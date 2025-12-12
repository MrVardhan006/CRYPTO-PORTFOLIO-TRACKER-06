import requests
from flask import Blueprint, render_template
from flask_login import login_required
import base64
import matplotlib.pyplot as plt
from io import BytesIO

bp = Blueprint('recommend', __name__)

@bp.route('/recommend')
@login_required
def recommend():
    recommended = []
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'inr',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': 'true'
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status() 
        coins = res.json()

        if not isinstance(coins, list):
            print("Unexpected API response:", coins)
            coins = []

        recommended = [coin for coin in coins if coin.get('price_change_percentage_24h') is not None and coin.get('price_change_percentage_24h') > 1.5]
        recommended = sorted(
            recommended,
            key=lambda c: (c.get('market_cap', 0), c.get('total_volume', 0)),
            reverse=True
        )[:10]

        for coin in recommended:
            sparkline = coin.get('sparkline_in_7d', {}).get('price', [])
            if sparkline:
                try:
                    fig, ax = plt.subplots(figsize=(2, 0.5))
                    color = '#21d07a' if (coin.get('price_change_percentage_24h') or 0) > 0 else '#ff6b6b'
                    ax.plot(sparkline, color=color)
                    ax.axis('off')
                    buf = BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
                    plt.close(fig)
                    buf.seek(0)
                    coin['sparkline_img'] = base64.b64encode(buf.read()).decode('utf-8')
                except Exception as e:
                    print(f"Sparkline error for {coin.get('name')}: {e}")
                    coin['sparkline_img'] = ''
            else:
                coin['sparkline_img'] = ''

    except requests.exceptions.RequestException as e:
        print("Error fetching data from CoinGecko:", e)
        recommended = []

    except Exception as e:
        print("Unexpected error:", e)
        recommended = []

    return render_template('recommend.html', recommended=recommended)
