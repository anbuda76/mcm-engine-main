"""
app/routes/admin.py
───────────────────
Blueprint pannello amministrazione.

Route:
  GET       /admin/                   → dashboard admin (utenti + cache + upload)
  GET/POST  /admin/users/new          → crea nuovo utente
  GET/POST  /admin/users/<id>/edit    → modifica utente
  POST      /admin/users/<id>/delete  → elimina utente
  POST      /admin/users/<id>/toggle  → abilita/disabilita utente
  POST      /admin/upload             → upload Excel (Comportamento / Performance)
  POST      /admin/cache/reload       → forza invalidazione + reload cache
"""

import os
import json
from functools import wraps
from flask import (Blueprint, render_template, redirect, url_for,
                   request, jsonify, flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import db, User, ALL_MODULES, ALL_AGENTS
from app.data_cache import invalidate, get_cache_info, get_specializzazioni, get_aziende
from app.ai.agent_registry import AGENTS as AGENT_DEFS

admin_bp = Blueprint("admin", __name__)

ALLOWED_EXCEL = {"xlsx", "xls"}

# Mappa nome file → nome atteso in data_raw/
EXCEL_FILES = {
    "comportamento": "Comportamento HCP.xlsx",
    "performance":   "Performance Channel.xlsx",
}


def admin_required(f):
    """Decoratore: solo utenti admin possono accedere."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({"error": "Accesso negato"}), 403
        return f(*args, **kwargs)
    return decorated


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXCEL


# ──────────────────────────────────────────────────────────────
# Dashboard admin
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/")
@admin_required
def index():
    users      = User.query.order_by(User.created_at).all()
    cache_info = get_cache_info()

    # Lista target e aziende dal dataset (per il form utente)
    try:
        all_targets = get_specializzazioni()
        all_aziende = get_aziende()
    except Exception:
        all_targets = []
        all_aziende = []

    return render_template(
        "admin/index.html",
        active_page="admin",
        users=users,
        cache_info=cache_info,
        all_modules=ALL_MODULES,
        all_targets=all_targets,
        all_aziende=all_aziende,
        excel_files=EXCEL_FILES,
    )


# ──────────────────────────────────────────────────────────────
# Crea utente
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    try:
        all_targets = get_specializzazioni()
        all_aziende = get_aziende()
    except Exception:
        all_targets = []
        all_aziende = []

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = request.form.get("is_admin") == "1"
        modules  = request.form.getlist("modules")
        targets  = request.form.getlist("targets")
        aziende  = request.form.getlist("aziende")
        agents   = request.form.getlist("agents")

        if not username or not password:
            error = "Username e password sono obbligatori."
        elif User.query.filter_by(username=username).first():
            error = f"Username '{username}' già esistente."
        else:
            u = User()
            u.username   = username
            u.set_password(password)
            u.is_admin   = is_admin
            u._is_active = True
            u.modules    = modules
            u.targets    = targets
            u.aziende    = aziende
            u.agents     = agents
            db.session.add(u)
            db.session.commit()
            return redirect(url_for("admin.index"))

    return render_template(
        "admin/user_form.html",
        active_page="admin",
        user=None,
        all_modules=ALL_MODULES,
        all_agents=ALL_AGENTS,
        agent_defs=AGENT_DEFS,
        all_targets=all_targets,
        all_aziende=all_aziende,
        error=error,
        action_label="Crea utente",
    )


# ──────────────────────────────────────────────────────────────
# Modifica utente
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(user_id):
    u = db.session.get(User, user_id)
    if u is None:
        return redirect(url_for("admin.index"))

    try:
        all_targets = get_specializzazioni()
        all_aziende = get_aziende()
    except Exception:
        all_targets = []
        all_aziende = []

    error = None
    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("password", "").strip()
        is_admin     = request.form.get("is_admin") == "1"
        modules      = request.form.getlist("modules")
        targets      = request.form.getlist("targets")
        aziende      = request.form.getlist("aziende")
        agents       = request.form.getlist("agents")

        existing = User.query.filter_by(username=new_username).first()
        if not new_username:
            error = "Username obbligatorio."
        elif existing and existing.id != u.id:
            error = f"Username '{new_username}' già in uso."
        else:
            u.username = new_username
            if new_password:
                u.set_password(new_password)
            u.is_admin = is_admin
            u.modules  = modules
            u.targets  = targets
            u.aziende  = aziende
            u.agents   = agents
            db.session.commit()
            return redirect(url_for("admin.index"))

    return render_template(
        "admin/user_form.html",
        active_page="admin",
        user=u,
        all_modules=ALL_MODULES,
        all_agents=ALL_AGENTS,
        agent_defs=AGENT_DEFS,
        all_targets=all_targets,
        all_aziende=all_aziende,
        error=error,
        action_label="Salva modifiche",
    )


# ──────────────────────────────────────────────────────────────
# Elimina utente
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    u = db.session.get(User, user_id)
    if u and u.id != current_user.id:  # non cancellare se stesso
        db.session.delete(u)
        db.session.commit()
    return redirect(url_for("admin.index"))


# ──────────────────────────────────────────────────────────────
# Abilita / Disabilita utente
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def user_toggle(user_id):
    u = db.session.get(User, user_id)
    if u and u.id != current_user.id:
        u._is_active = not u._is_active
        db.session.commit()
    return redirect(url_for("admin.index"))


# ──────────────────────────────────────────────────────────────
# Upload Excel
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/upload", methods=["POST"])
@admin_required
def upload_excel():
    file_type = request.form.get("file_type", "")  # "comportamento" | "performance"

    if file_type not in EXCEL_FILES:
        return jsonify({"error": "Tipo file non valido."}), 400

    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "Nessun file selezionato."}), 400

    f = request.files["file"]
    if not _allowed_file(f.filename):
        return jsonify({"error": "Formato non supportato. Usa .xlsx o .xls"}), 400

    dest_name = EXCEL_FILES[file_type]
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = os.path.join(upload_dir, dest_name)

    try:
        f.save(dest_path)
        invalidate()  # forza reload al prossimo get_data()
        return jsonify({
            "ok":      True,
            "message": f"File '{dest_name}' caricato. Cache invalidata.",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────
# Forza reload cache
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/cache/reload", methods=["POST"])
@admin_required
def cache_reload():
    try:
        invalidate()
        # Trigger precaricamento immediato
        from app.data_cache import get_data, get_cache_info
        get_data()
        info = get_cache_info()
        return jsonify({"ok": True, "cache": info})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────
# Stato cache (per polling dashboard)
# ──────────────────────────────────────────────────────────────
@admin_bp.route("/cache/info")
@admin_required
def cache_info_api():
    return jsonify(get_cache_info())
