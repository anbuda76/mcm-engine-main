"""
app/models.py
─────────────
Modelli SQLAlchemy per MCM Engine.

Tabella: users
  - Permessi per modulo (comportamento / performance / trend)
  - Filtro target medici (specializzazioni) — [] = tutti
  - Filtro aziende — [] = tutte
"""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Moduli disponibili (escluso ai — gestito separatamente)
ALL_MODULES = ["comportamento", "performance", "trend"]

# Agenti AI disponibili
ALL_AGENTS  = ["comportamento", "performance"]


class User(db.Model, UserMixin):
    __tablename__ = "mcm_users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)
    _is_active    = db.Column("is_active", db.Boolean, default=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Permessi come stringhe JSON
    # modules: lista moduli abilitati, es. '["comportamento","performance"]'
    # targets: lista specializzazioni, '[]' = tutte
    # aziende: lista aziende,          '[]' = tutte
    _modules = db.Column("modules", db.Text,
                         default='["comportamento","performance","trend"]',
                         nullable=False)
    _targets = db.Column("targets", db.Text, default="[]", nullable=False)
    _aziende = db.Column("aziende", db.Text, default="[]", nullable=False)
    # Agenti AI abilitati — [] = tutti; lista esplicita = solo quelli elencati
    _agents  = db.Column("agents",  db.Text, default="[]", nullable=False)

    # ── Password ────────────────────────────────────────────────
    def set_password(self, pw: str) -> None:
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)

    # ── Flask-Login: is_active ───────────────────────────────────
    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, val: bool) -> None:
        self._is_active = val

    # ── Permessi: modules ────────────────────────────────────────
    @property
    def modules(self) -> list:
        try:
            return json.loads(self._modules or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @modules.setter
    def modules(self, val: list) -> None:
        self._modules = json.dumps(val or [])

    # ── Permessi: targets ────────────────────────────────────────
    @property
    def targets(self) -> list:
        try:
            return json.loads(self._targets or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @targets.setter
    def targets(self, val: list) -> None:
        self._targets = json.dumps(val or [])

    # ── Permessi: aziende ────────────────────────────────────────
    @property
    def aziende(self) -> list:
        try:
            return json.loads(self._aziende or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @aziende.setter
    def aziende(self, val: list) -> None:
        self._aziende = json.dumps(val or [])

    # ── Helper: verifica accesso modulo ─────────────────────────
    def has_module(self, module: str) -> bool:
        """Admin bypassa sempre. Utente normale deve avere il modulo nella lista."""
        if self.is_admin:
            return True
        return module in self.modules

    # ── Helper: filtra liste per permessi ───────────────────────
    def filter_targets(self, all_targets: list) -> list:
        """[] = nessuna restrizione; admin vede tutto."""
        if self.is_admin or not self.targets:
            return all_targets
        allowed = set(self.targets)
        return [t for t in all_targets if t in allowed]

    def filter_aziende(self, all_aziende: list) -> list:
        """[] = nessuna restrizione; admin vede tutto."""
        if self.is_admin or not self.aziende:
            return all_aziende
        allowed = set(self.aziende)
        return [a for a in all_aziende if a in allowed]

    # ── Permessi: agents ─────────────────────────────────────────
    @property
    def agents(self) -> list:
        try:
            return json.loads(self._agents or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @agents.setter
    def agents(self, val: list) -> None:
        self._agents = json.dumps(val or [])

    def has_agent(self, agent_key: str) -> bool:
        """Admin bypassa. Lista vuota = tutti gli agenti abilitati."""
        if self.is_admin:
            return True
        return not self.agents or agent_key in self.agents

    def __repr__(self) -> str:
        role = "admin" if self.is_admin else "user"
        return f"<User {self.username!r} [{role}]>"
