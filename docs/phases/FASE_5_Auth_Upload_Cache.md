# FASE 5 — Auth, Upload File, Cache TTL

**Stato**: ✅ Completata
**Data**: 2026-03-05

---

## Obiettivo

Implementare sistema multi-utente con:
- Autenticazione (Flask-Login + SQLite)
- Permessi granulari per modulo / target medici / aziende
- Upload file Excel via pannello admin
- Cache dati con TTL configurabile e widget status in dashboard

---

## Dipendenze aggiunte

```
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
```

---

## File creati / modificati

### Nuovi file
| File | Descrizione |
|------|-------------|
| `app/models.py` | User model con permessi JSON |
| `app/routes/auth.py` | Blueprint login/logout |
| `app/routes/admin.py` | Blueprint pannello admin |
| `app/templates/auth/login.html` | Pagina login dark theme |
| `app/templates/admin/index.html` | Pannello admin (utenti + cache + upload) |
| `app/templates/admin/user_form.html` | Form crea/modifica utente |
| `instance/mcm.db` | SQLite database (creato auto all'avvio) |

### File modificati
| File | Modifica |
|------|----------|
| `requirements.txt` | + Flask-Login, Flask-SQLAlchemy |
| `config/__init__.py` | + SQLALCHEMY_DATABASE_URI, CACHE_TTL_HOURS, UPLOAD_FOLDER, ADMIN_USERNAME, ADMIN_PASSWORD |
| `app/__init__.py` | + db.init_app, login_manager, context_processor, registra auth_bp + admin_bp, auto-create admin |
| `app/data_cache.py` | + TTL logic, get_cache_info(), get_aziende(), invalidate() |
| `app/routes/dashboard.py` | + @login_required, passa cache_info al template |
| `app/routes/modulo1.py` | + @login_required su tutte le route, filter_targets() |
| `app/routes/modulo2.py` | + @login_required su tutte le route, filter_aziende() + filter_targets() |
| `app/routes/trend.py` | + @login_required su tutte le route, filter_aziende() + filter_targets() |
| `app/templates/base.html` | + topbar user/logout/admin, sidebar nav filtrата per modulo, Admin link |
| `app/templates/dashboard/index.html` | + cache status widget (4 cards), FASE 5 wip |

---

## Architettura Auth

### User model

```python
class User(db.Model, UserMixin):
    id            # PK
    username      # unico
    password_hash # werkzeug hash
    is_admin      # bypass tutti i permessi
    _is_active    # abilita/disabilita account
    _modules      # JSON: ["comportamento", "performance", "trend"]
    _targets      # JSON: [] = tutte le spec.; ["Cardiologo", ...] = filtro
    _aziende      # JSON: [] = tutte; ["AZ Focus", ...] = filtro
```

### Semantica permessi
- `[] = nessuna restrizione` (vede tutto)
- Lista non vuota = mostra solo gli elementi della lista
- `is_admin=True` → bypassa tutto, equivale a [] su tutti i campi

### Admin di default
All'avvio con DB vuoto, crea admin da `ADMIN_USERNAME`/`ADMIN_PASSWORD` in config (default: `admin`/`changeme`). Attenzione: warning se password è ancora "changeme".

---

## Pannello Admin (`/admin/`)

### Route
| Route | Metodo | Funzione |
|-------|--------|----------|
| `/admin/` | GET | Lista utenti + cache info + upload |
| `/admin/users/new` | GET/POST | Crea utente |
| `/admin/users/<id>/edit` | GET/POST | Modifica utente |
| `/admin/users/<id>/delete` | POST | Elimina (non se stesso) |
| `/admin/users/<id>/toggle` | POST | Attiva/disattiva account |
| `/admin/upload` | POST | Upload Excel → `data_raw/`, invalida cache |
| `/admin/cache/reload` | POST | Invalida + ricarica cache |
| `/admin/cache/info` | GET | Stato cache JSON |

### Protezione
`admin_required` decorator = `@login_required` + check `current_user.is_admin`.

---

## Cache TTL

```python
# data_cache.py
def _ttl_hours():
    # legge CACHE_TTL_HOURS da Flask config o env (default: 8)

def get_cache_info():
    return {
        "loaded_at":   "2026-03-05 10:30",  # stringa formattata
        "expires_at":  "2026-03-05 18:30",
        "remaining_m": 420,                  # minuti rimanenti
        "n_beh":       1250,
        "n_perf":      3800,
        "ttl_hours":   8,
    }

def invalidate():
    # forza _cache['loaded_at'] = None → ricarica al prossimo get_data()
```

Dashboard mostra: n_beh/n_perf nei card Excel + card "Cache Dati" con minuti rimanenti.

---

## base.html — Modifiche UI

### Topbar (right side)
- Avatar + username utente corrente
- Link "Admin" (solo admin) → `/admin/`
- Bottone "Esci" → `/auth/logout`

### Sidebar nav
```jinja2
{% if 'comportamento' in user_modules %}  <!-- Comportamento link -->
{% if 'performance' in user_modules %}    <!-- Performance link -->
{% if 'trend' in user_modules %}          <!-- Trend link -->
{% if current_user_is_admin %}            <!-- Pannello Admin link (warning color) -->
```

Il context processor in `__init__.py` inietta `user_modules` e `current_user_is_admin` in tutti i template.

---

## Form Utente (`/admin/users/new` e `/admin/users/<id>/edit`)

Campi:
- Username + Password (required solo in creazione)
- Checkbox is_admin
- Checkbox multi-modulo (comportamento / performance / trend)
- Scrollable list target medici (select-all/deselect-all)
- Scrollable list aziende (select-all/deselect-all)

---

## Upload Excel

- Zona drag & drop per **Comportamento HCP** e **Performance Channel**
- Salva in `data_raw/` con nome fisso (sostituisce il file esistente)
- Dopo upload: chiama `invalidate()` → prossima analisi ricarica i dati
- Admin può anche fare "Forza ricarica cache" senza upload (utile dopo modifica file manuale)

---

## Verifica funzionamento

1. `venv\Scripts\python run.py`
2. Aprire `http://localhost:5000` → redirect a `/login`
3. Login con `admin` / `changeme`
4. Dashboard: verificare 4 card Stato Sistema con n_beh, n_perf, cache TTL
5. Sidebar: tutti e 3 i moduli visibili + "Pannello Admin"
6. `/admin/` → creare utente con soli moduli specifici e/o target/aziende
7. Logout + login con nuovo utente → verificare sidebar filtrata
8. Tentare accesso diretto a `/modulo1/` senza login → redirect a `/login`
