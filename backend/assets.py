import matplotlib.pyplot as plt
import base64
from io import BytesIO
from flask import Blueprint, render_template, request, flash
from flask_login import login_required

bp = Blueprint('assets', __name__)

@bp.route('/assets', methods=['GET', 'POST'])
@login_required
def assets_page():
    error = None
    final_value = None
    gain = None
    years = None
    graph_url = None
    if request.method == 'POST':
        try:
            initial_investment = float(request.form.get('initial_investment', 0))
            years = int(request.form.get('years', 0))
            assets = request.form.getlist('assets')
            allocations = {a: float(request.form.get(f'allocation_{a.replace(" ", "")}', 0)) for a in assets}
            returns = {a: float(request.form.get(f'return_{a.replace(" ", "")}', 0)) for a in assets}
            if not assets:
                error = 'Please select at least one asset.'
            elif sum(allocations.values()) != 100:
                error = 'Total allocation must be 100%.'
            else:
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
        except Exception as e:
            error = str(e)
    return render_template('assets.html', error=error, final_value=final_value, gain=gain, years=years, graph_url=graph_url, request=request)
