from flask import Blueprint, render_template
from flask_login import login_required
from app.data_cache import get_cache_info

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    """Homepage — panoramica KPI aggregati."""
    return render_template("dashboard/index.html",
                           active_page="dashboard",
                           cache_info=get_cache_info())
