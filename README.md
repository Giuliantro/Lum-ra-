# Luméra — AI Personal Stylist

> Scopri i colori, i capelli e lo stile che parlano di te.

- **backend/** — FastAPI (Python): API, board e prove con GPT Image 2, PostgreSQL (SQLAlchemy + Alembic), autenticazione Clerk.
- **frontend/** — Vite + React + TypeScript, login e registrazione con Clerk.

Documentazione tecnica completa: [docs.md](docs.md).

## Prerequisiti

- **Clerk**: crea un'applicazione su clerk.com. In *User & authentication* abilita email, nome e cognome. Da *API keys* copia la publishable key e la secret key.
- **PostgreSQL**: in locale usa l'URL **pubblico** del database Railway (`DATABASE_PUBLIC_URL`, host `*.proxy.rlwy.net`). `postgres.railway.internal` funziona solo per i servizi deployati su Railway.

## Avvio

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # poi compila OPENAI_API_KEY, DATABASE_URL, CLERK_SECRET_KEY, CLERK_PUBLISHABLE_KEY
alembic upgrade head              # crea le tabelle nel database
uvicorn app.main:app --reload --port 8000

# Frontend (altro terminale)
cd frontend
npm install
copy .env.example .env            # poi compila VITE_CLERK_PUBLISHABLE_KEY
npm run dev                       # http://localhost:5173 (proxy /api → :8000)
```

## Architettura

Tutto passa da **GPT Image 2** (`images.edit`): non c'è un modello di analisi testuale né output JSON.
L'analisi viene restituita come **board** (immagini editoriali con testo in italiano), e le prove sulla foto usano un pannello della board come riferimento visivo.

| Fase | Endpoint | Immagini in input → output |
|---|---|---|
| Upload ritratto | `POST /api/profiles` | ritratto → board **Stagione & palette** |
| Nuova foto | `POST /api/profiles/{id}/photo` | rigenera le board, stile e salvati restano |
| Scelta stile | `POST /api/profiles/{id}/style` | ritratto + board stagione → board **Capelli**, **Colore**, **Outfit**, **Accessori** (in parallelo, 3 pannelli numerati ciascuna) |
| Rigenera board | `POST /api/profiles/{id}/boards/{kind}/regenerate` | + versione precedente, guidata da ♥/✕ sui pannelli |
| Prova singola | `POST /api/profiles/{id}/images` | foto corrente + board → foto modificata (pannello 1/2/3) |
| Look completo | `POST /api/profiles/{id}/looks/{1-3}/visualize` | catena taglio → colore → outfit → occhiali con lo stesso numero di pannello |
| Feedback | `POST /api/profiles/{id}/feedback` | LIKE / DISLIKE su `<board_id>:<pannello>`, SAVE su immagini |

- Prompt delle board: [backend/app/prompts/boards.py](backend/app/prompts/boards.py) — prompt delle prove (blocchi di preservazione del Prompt Pack): [backend/app/prompts/image_templates.py](backend/app/prompts/image_templates.py).
- Ogni immagine salva prompt e versione (`prompt_version`) ed è un nodo dell'albero (`parent_image_id`) → annulla e ramificazioni.
- `input_fidelity` non viene mai inviato; le prove seguono l'aspetto della foto (1024x1536 per i ritratti), le board usano `BOARD_SIZE`.

## Configurazione (`backend/.env`)

| Variabile | Default | Note |
|---|---|---|
| `IMAGE_MODEL` | `gpt-image-2` | |
| `DATABASE_URL` | — | URL PostgreSQL (`postgresql://…`) |
| `CLERK_SECRET_KEY` / `CLERK_PUBLISHABLE_KEY` | — | Chiavi Clerk del backend |
| `BOARD_QUALITY` / `BOARD_SIZE` | `high` / `1536x1024` | le board contengono testo: tieni qualità alta |
| `PREVIEW_QUALITY` / `FINAL_QUALITY` | `medium` / `high` | qualità delle prove sulla foto |
