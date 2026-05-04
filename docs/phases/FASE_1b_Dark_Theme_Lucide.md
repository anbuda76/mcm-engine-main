# FASE 1b — Dark Theme + Lucide Icons + Behavioral UI

**Data**: 26 febbraio 2026
**Stato**: ✅ Completata

---

## Modifiche applicate

### 1. `app/templates/base.html`
- Dark theme completo: `bg-surface-900` (#0d1117), surface palette stratificata
- **Lucide Icons** integrati via CDN (`unpkg.com/lucide`)
- Font **Inter** da Google Fonts
- Sidebar ridisegnata:
  - Logo con `brain-circuit` icon + glow accent
  - Nav items con indicatore laterale accent (barra verde sinistra)
  - State attivo: `bg-accent/15 border border-accent/20 text-accent`
  - Hover: `bg-white/6` senza bordo
  - Footer con status dot animato
- Topbar dark: breadcrumb BHAVE > PageTitle + indicatori destra
- Toggle sidebar: classe `.collapsed` via CSS transition

### 2. `app/static/css/custom.css` — riscrittura completa
- CSS Variables: `--accent`, `--surface-*`, `--border`, `--text-muted`
- **Micro-animazioni behavioral per icone Lucide**:
  - `settings-2` → rotazione 45° al hover
  - `trending-up` → translateY(-2px) al hover
  - `brain-circuit` → drop-shadow glow permanente
  - `users-round` → scale(1.12) al hover
  - `bar-chart-3` → scaleY crescita dal basso al hover
  - `layout-dashboard` → zoom al hover
- `.kpi-card` — dark card con hover lift + border accent
- `.module-card` — card navigazione con top-border gradient al hover
- `.tab-bar` / `.tab-btn` — tab system pill-style dark
- `.chart-container` — container dark per grafici Plotly
- `.gradient-banner` — hero banner con decorazioni geometriche
- `.badge` — badge/pill sistema (accent, warning, muted)
- `.dark-table` — tabelle dark
- `.dark-select` / `.dark-input` — form elements dark

### 3. `app/templates/dashboard/index.html`
- Gradient banner con icona brain-circuit
- 4 Module Cards con icone Lucide colorate + arrow-right animato
- 3 Stato Sistema cards con status dot animato
- Progress tracker migrazione con check icons

### 4. Template placeholder aggiornati
- `modulo1/index.html`, `modulo2/index.html`, `trend/index.html`
- Icone Lucide contestuali per ogni modulo
- Badge stato coerenti con sistema

---

## Libreria icone scelta: Lucide Icons

**Motivazione behavioral**:
- Outline stroke uniforme (1.5px) — leggibilità alta su dark
- Nomi semantici che comunicano azione: `trending-up`, `users-round`, `brain-circuit`, `sliders-horizontal`
- Facilmente animabili via CSS transform
- CDN: `unpkg.com/lucide@latest/dist/umd/lucide.min.js`

**Inizializzazione**: `lucide.createIcons()` chiamata in ogni template via `{% block scripts %}`

---

## Test
```
OK / -> 200
OK /modulo1/ -> 200
OK /modulo2/ -> 200
OK /trend/ -> 200
OK /api/health -> 200
```

---

## Prossimo: FASE 2 — Modulo 1 Comportamento HCP
