# Luméra — Documentazione del codice

Guida tecnica per chi sviluppa su Luméra: struttura del progetto, flusso dei dati, moduli backend e frontend, API e punti di estensione.

> Avvio rapido e configurazione: vedi [README.md](README.md).

---

## 1. Panoramica

Luméra è un personal stylist AI composto da:

| Parte | Tecnologia | Ruolo |
|---|---|---|
| `backend/` | Python, FastAPI, SQLAlchemy (async), Alembic, OpenAI SDK, PyJWT, Pillow | API REST, autenticazione, prompt, chiamate a GPT Image 2, persistenza su PostgreSQL |
| `frontend/` | Vite, React 19, TypeScript, `@clerk/react` | Interfaccia: accesso e registrazione, onboarding, upload, scelta stile, board, studio di prova |
| PostgreSQL (Railway) | — | Utenti, profili, immagini, scelte di stile, feedback |
| Clerk | — | Registrazione, login e sessioni (token JWT) |

**Principio architetturale:** tutto il lavoro AI è svolto da **GPT Image 2** tramite l'endpoint `images.edit`. Non esiste un modello di analisi testuale e non ci sono output JSON dal modello:

- l'**analisi** (stagione cromatica, palette, hairstyle, colore, outfit, accessori) è restituita come **board**: un'immagine editoriale con testo in italiano;
- le **prove sulla foto** sono edit della foto dell'utente che usano **un pannello numerato di una board** come riferimento visivo.

---

## 2. Struttura del progetto

```text
backend/
├── .env.example              Variabili d'ambiente (copiare in .env)
├── requirements.txt
├── alembic.ini               Config Alembic (l'URL arriva da DATABASE_URL)
├── migrations/
│   ├── env.py                Ambiente Alembic async, legge Base.metadata
│   └── versions/
│       └── 0001_initial_schema.py   Creazione di tutte le tabelle
└── app/
    ├── main.py               App FastAPI, CORS, gestione errori, /api/health
    ├── config.py             Settings (pydantic-settings, legge .env)
    ├── db.py                 Engine async, sessionmaker, dipendenza get_session
    ├── db_models.py          Tabelle ORM: users, lumera_profiles, images, style_choices, feedback_events
    ├── auth.py               Verifica del token Clerk, creazione utente, dipendenze current_user / onboarded_user
    ├── models.py             Modelli Pydantic delle API
    ├── storage.py            Accesso ai dati (query sempre filtrate per utente)
    ├── prompts/
    │   ├── boards.py         Prompt delle board di analisi (versionati)
    │   └── image_templates.py  Prompt delle prove sulla foto (versionati)
    ├── services/
    │   ├── generation.py     Chiamate a GPT Image 2: board, prove, orchestrazione
    │   └── imaging.py        Normalizzazione upload, scelta della size
    └── routers/
        ├── users.py          /api/me (account, onboarding, cancellazione dati)
        └── profiles.py       /api/profiles/... (stylist)

frontend/
├── .env.example              VITE_CLERK_PUBLISHABLE_KEY, VITE_API_URL (vuoto in locale)
├── vite.config.ts            Proxy /api → http://127.0.0.1:8000 (timeout 10 min)
├── index.html                Font (Cormorant Garamond, Inter), lingua it
└── src/
    ├── main.tsx              Bootstrap React + ClerkProvider
    ├── App.tsx               Landing (anonimo) / Workspace (autenticato): stato, schede, azioni
    ├── api.ts                Client HTTP tipizzato con token Clerk, cache delle immagini
    ├── types.ts              Tipi speculari a backend/app/models.py
    ├── labels.ts             Etichette UI in italiano, mapping board → operazione
    ├── index.css             Design token e stili (tema chiaro/scuro)
    └── components/
        ├── Landing.tsx       Pagina pubblica con Registrati / Accedi (modali Clerk)
        ├── Onboarding.tsx    Nome, cognome, età (primo accesso e "I miei dati")
        ├── AuthImage.tsx     <img> per immagini protette (fetch con token → object URL)
        ├── Upload.tsx        Caricamento ritratto (drag & drop)
        ├── StylePicker.tsx   Scelta stile primario/secondario e preferenze
        ├── Board.tsx         Visualizzazione board + azioni per pannello
        └── Studio.tsx        Prove sulla foto, cronologia, annulla, salva
```

---

## 3. Flusso applicativo

```text
Registrazione / login (Clerk)
   │  GET /api/me → crea la riga in users al primo accesso
   ▼
Onboarding: nome, cognome, età
   │  PUT /api/me   (finché non è completo, /api/profiles risponde 403)
   ▼
Upload ritratto
   │  POST /api/profiles
   ▼
normalize_upload (EXIF, RGB, max 2048px, PNG)
   │
   ▼
Board SEASON  ◄── input: [ritratto]
   │  status = "analyzed"
   ▼
Scelta stile
   │  POST /api/profiles/{id}/style
   ▼
Board HAIR ‖ HAIR_COLOR ‖ OUTFIT ‖ ACCESSORIES   (asyncio.gather)
   │  input: [ritratto, board SEASON]
   │  status = "styled"
   ▼
Prova sulla foto (pannello 1, 2 o 3)
   │  POST /api/profiles/{id}/images
   │  input: [foto corrente, board di riferimento]
   ▼
Nuovo nodo immagine (figlio della foto corrente)
   │
   ├── Salva / Scarica / Annulla (torna al genitore)
   └── ♥ / ✕ sui pannelli → Rigenera board (riceve anche la versione precedente)
```

### Stati del profilo

| `status` | Significato | Cosa mostra il frontend |
|---|---|---|
| `created` | Profilo creato, board stagione non ancora generata (o generazione fallita) | Upload |
| `analyzed` | Board `SEASON` disponibile | Board stagione + scelta stile |
| `styled` | Tutte e 5 le board disponibili | Schede: colori, capelli, look, accessori, studio, stile |

---

## 4. Backend

### 4.1 `config.py`

`Settings` legge le variabili da `backend/.env` (le maiuscole/minuscole non contano). `get_settings()` è memorizzata con `lru_cache`.

| Campo | Default | Uso |
|---|---|---|
| `openai_api_key` | `""` | Se vuota, l'SDK usa `OPENAI_API_KEY` dall'ambiente |
| `image_model` | `gpt-image-2` | Modello per board e prove |
| `image_output_format` | `webp` | Formato delle immagini generate |
| `board_quality` / `board_size` | `high` / `1536x1024` | Board (contengono testo → qualità alta) |
| `preview_quality` / `final_quality` | `medium` / `high` | Prove in modalità anteprima / alta qualità |
| `database_url` | `""` | URL PostgreSQL (`postgresql://…`, convertito in `postgresql+asyncpg://`) o `sqlite+aiosqlite://…` per i test |
| `clerk_secret_key` | `""` | Chiave segreta Clerk: usata per leggere email e nome dall'API di Clerk |
| `clerk_publishable_key` | `""` | Da qui si ricava il Frontend API di Clerk e quindi l'URL JWKS |
| `clerk_jwks_url` | derivato | Override dell'URL JWKS |
| `clerk_authorized_parties` | `cors_origins` | Origini ammesse nel claim `azp` del token |
| `cors_origins` | `["http://localhost:5173"]` | Origini consentite (JSON in `.env`) |

### 4.2 `models.py`

Modelli Pydantic delle API (la persistenza è in `db_models.py`).

**Utente**

- `UserOut`: `id`, `email`, `first_name`, `last_name`, `age`, `profile_complete` (vero quando nome, cognome ed età sono presenti).
- `UserUpdate`: `first_name`, `last_name` (1–100 caratteri), `age` (14–120).

**`LumeraProfile`**: la risposta che descrive un profilo, ricostruita dal database a ogni richiesta.

| Campo | Tipo | Note |
|---|---|---|
| `id` | `str` | uuid hex |
| `status` | `created \| analyzed \| styled` | Vedi §3 |
| `original_image_id` | `str?` | Ritratto corrente (radice dell'albero delle prove) |
| `boards` | `dict[BoardKind, image_id]` | Versione **corrente** di ogni board; le precedenti restano in `images` |
| `style_request` | `StyleRequest?` | Ultime preferenze di stile (lo storico è in `style_choices`) |
| `user_feedback` | `UserFeedback` | `liked`, `disliked`, `saved`, calcolati dagli eventi |
| `images` | `list[ImageNode]` | Tutte le immagini: originali, board, prove |

`ProfileSummary` (`id`, `status`, `original_image_id`, `created_at`) è usato per l'elenco dei profili.

**`ImageNode`**: un'immagine e la sua provenienza.

| Campo | Note |
|---|---|
| `operation` | `ORIGINAL`, `BOARD`, `HAIR`, `HAIR_COLOR`, `OUTFIT`, `EYEWEAR` |
| `parent_image_id` | Per le prove: la foto da cui deriva. Forma l'albero (annulla, ramificazioni) |
| `board_kind` | Solo per `BOARD` |
| `reference_board_id`, `option` | Solo per le prove: board e pannello usati come riferimento |
| `setting` | Solo per le prove `OUTFIT`: location usata |
| `prompt_version` | Versione del prompt (il testo completo è salvato nel DB, colonna `images.prompt`) |
| `quality`, `size`, `created_at` | Metadati di generazione |

**Richieste API**

- `StyleRequest`: `selected_styles` (1–2 elementi; il primo è primario), `trend_preference` (`low|moderate|high`), `occasion`, `comfort_preferences`, `free_text_style_request` (con limiti di lunghezza).
- `TryOnRequest`: `operation`, `option` (1–3), `parent_image_id` (default: originale), `mode` (`preview|final`), `setting` (solo per `OUTFIT`, vedi §4.8).
- `LookVisualizeRequest`: `parent_image_id`, `mode`, `include_eyewear`, `setting`.
- `FeedbackEntry`: `type` (`LIKE|DISLIKE|SAVE|TRY|REGENERATE|UNDO`), `entity_type` (`board_option|image`), `entity_id` (max 64 caratteri).
  - Per i pannelli: `entity_id = "<board_image_id>:<pannello>"`.
  - Per le immagini: `entity_id = "<image_id>"`.

### 4.3 Database: `db.py`, `db_models.py`, `storage.py`

PostgreSQL tramite SQLAlchemy 2 async (driver `asyncpg`). Lo schema è creato e versionato con **Alembic**.

```text
users ─┬─< lumera_profiles ─┬─< images
       │                    ├─< style_choices
       ├─< style_choices    └─< feedback_events
       └─< feedback_events
```

| Tabella | Contenuto | Colonne principali |
|---|---|---|
| `users` | Un utente registrato | `id` (UUID), `clerk_user_id` (unico), `email`, `first_name`, `last_name`, `age` (CHECK 14–120), `created_at`, `updated_at` |
| `lumera_profiles` | Un ritratto con le sue board | `id`, `user_id`, `status`, `original_image_id`, `boards` (JSONB), `style_request` (JSONB) |
| `images` | Originali, board e prove | metadati di §4.2, `prompt` (TEXT), `mime`, `data` (BYTEA) |
| `style_choices` | **Storico** di ogni scelta di stile | `selected_styles` (JSONB), `trend_preference`, `occasion`, `comfort_preferences`, `free_text_style_request`, `created_at` |
| `feedback_events` | Ogni ♥, ✕ e salvataggio | `type`, `entity_type`, `entity_id`, `created_at` |

Scelte di progetto:

- **Le immagini stanno nel database** (`images.data`, caricata in modo differito): il filesystem dei servizi Railway non è persistente. Il limite è il peso del database (vedi §9).
- **Cancellazione a cascata** (`ON DELETE CASCADE`): eliminare un utente elimina profili, immagini, scelte e feedback.
- **Isolamento:** ogni funzione di `storage.py` che legge un profilo filtra per `user_id`; il profilo di un altro utente risulta "non trovato" (404).
- **Feedback come eventi:** `feedback_state()` ripercorre gli eventi in ordine; per ogni pannello vale l'ultimo voto tra LIKE e DISLIKE.
- **Transazioni brevi:** `generation.py` fa commit prima di ogni chiamata a GPT Image 2, così nessuna connessione resta aperta durante l'attesa.

Funzioni principali di `storage.py`: `create_profile`, `get_profile`, `list_profiles`, `set_board`, `add_image`, `get_image`, `image_bytes`, `to_node`, `add_style_choice`, `add_feedback`, `feedback_state`, `to_api`.

**Migrazioni**

```bash
cd backend
alembic upgrade head                                  # crea/aggiorna le tabelle
alembic revision --autogenerate -m "descrizione"      # dopo una modifica a db_models.py
alembic check                                         # verifica che modelli e DB coincidano
```

L'URL viene sempre da `DATABASE_URL`, mai da `alembic.ini`.

### 4.4 `auth.py`: autenticazione con Clerk

1. Il frontend ottiene il token di sessione con `useAuth().getToken()` e lo invia come `Authorization: Bearer <jwt>`.
2. `verify_token()` lo verifica localmente:
   - firma RS256 con le chiavi JWKS di Clerk (`PyJWKClient`, cache di 1 ora);
   - `exp`, `nbf` e `sub` obbligatori (tolleranza 5 secondi);
   - `azp`, se presente, deve essere tra le origini ammesse;
   - una sessione con `sts = pending` viene rifiutata.
3. `current_user` cerca l'utente per `clerk_user_id`. Al primo accesso legge email principale, nome e cognome dall'API di Clerk (`GET /v1/users/{id}` con `CLERK_SECRET_KEY`) e crea la riga. Due richieste simultanee al primo accesso sono gestite (vincolo di unicità + nuova lettura).
4. `onboarded_user` aggiunge il requisito di onboarding completo: senza nome, cognome ed età le API dello stylist rispondono **403**.

L'età resta nei dati dell'account e **non viene mai inserita nei prompt** (regola del Prompt Pack).

### 4.5 `services/imaging.py`

| Funzione | Descrizione |
|---|---|
| `normalize_upload(bytes)` | Applica la rotazione EXIF, converte in RGB, ridimensiona a max 2048px e restituisce PNG. Solleva `ValueError` (→ HTTP 400) se l'immagine non è valida |
| `output_size_for(bytes)` | Sceglie la size in base all'aspetto di un'immagine: verticale → `1024x1536`, orizzontale → `1536x1024`, quasi quadrata → `1024x1024` |

### 4.6 `services/generation.py`

Il cuore del backend. Tutte le chiamate al modello passano da `_edit()`.

| Funzione | Descrizione |
|---|---|
| `client()` | `AsyncOpenAI` singleton |
| `_edit(images, prompt, size, quality)` | Chiama `images.edit` con una lista di immagini `(nome, bytes, mime)` e restituisce i byte decodificati da `b64_json`. **Non invia mai `input_fidelity`** |
| `style_text(req)` | Converte `StyleRequest` nel blocco "STYLE DIRECTION" del prompt. I testi liberi dell'utente sono inseriti **tra virgolette come preferenze**, non come istruzioni |
| `_board_request(session, profile, kind)` | Legge dal DB le immagini di input e costruisce il prompt di una board |
| `_generate_boards(session, profile, kinds)` | Prepara le richieste, fa commit, chiama GPT Image 2 in parallelo e salva le board |
| `analyze(session, profile)` | Genera la board `SEASON` → `status = analyzed` → commit |
| `build_style_boards(session, user, profile, req)` | Salva la scelta in `style_choices`, genera le 4 board di stile in parallelo → `status = styled` → commit |
| `regenerate_board(session, profile, kind)` | Nuova versione di una board, poi commit |
| `try_on(session, profile, operation, option, parent, mode, setting)` | Edit della foto `parent` usando il pannello `option` della board corrispondente; salva l'immagine figlia e la restituisce |

**Immagini in input per ogni chiamata**

| Chiamata | Immagine 1 | Immagine 2 | Immagine 3 |
|---|---|---|---|
| Board `SEASON` | ritratto | — | — |
| Board di stile | ritratto | board `SEASON` | versione precedente della stessa board (solo se ha voti ♥/✕) |
| Prova | foto corrente (`parent`) | board di riferimento | — |

**Mapping operazione → board** (`image_templates.TEMPLATES`):

| Operazione | Board di riferimento |
|---|---|
| `HAIR` | `HAIR` |
| `HAIR_COLOR` | `HAIR_COLOR` |
| `OUTFIT` | `OUTFIT` |
| `EYEWEAR` | `ACCESSORIES` |

**Vincoli applicati da `try_on`**

- la board di riferimento deve esistere (altrimenti 400: "scegli prima il tuo stile");
- il `parent` non può essere una board (400);
- `OUTFIT` produce sempre una foto a figura intera `1024x1536` (`FULL_BODY_SIZE`);
- le altre operazioni seguono l'aspetto del `parent`, così una prova fatta dopo un outfit resta verticale a figura intera.

### 4.7 `prompts/boards.py`

Prompt delle board di analisi. Ogni board è un `BoardPrompt(kind, version, text)` con `version_tag` del tipo `BOARD_HAIR_V1.0`.

Il prompt finale è assemblato da `build(kind, style, liked, disliked)`:

```text
<testo specifico della board>
   └─ {option_panels} → OPTION_PANELS (layout a 3 pannelli + didascalie)
                          └─ {extra_caption} → EXTRA_CAPTION[kind]
   └─ {style}         → style_text(StyleRequest)
[+ FEEDBACK_BLOCK se ci sono voti sulla versione precedente]
+ COMMON_RULES (identità, etica, affidabilità, tipografia/layout)
```

| Board | Contenuto |
|---|---|
| `SEASON` | Ritratto invariato a sinistra. A destra: stagione (PRIMAVERA/ESTATE/AUTUNNO/INVERNO), descrittori, 12 colori, 6 neutri, 4 statement con nome e HEX, metalli, 5 colori "con attenzione". Titolo "Stagione probabile" se l'analisi è incerta |
| `HAIR` | 3 tagli; il colore attuale resta invariato |
| `HAIR_COLOR` | 3 colori; il taglio resta invariato; swatch del colore risultante |
| `OUTFIT` (v2.0) | 3 outfit coerenti con la palette, **a figura intera** (dalla testa alle scarpe), ognuno in una **location reale** diversa (ristorante, ufficio, giardino, …) coerente con l'outfit e l'occasione; la didascalia indica la location |
| `ACCESSORIES` | 3 montature di occhiali + striscia "Gioielli e accessori" |

L'inquadratura dei pannelli viene da `PANEL_FRAMING[kind]`; il default `HEAD_AND_SHOULDERS` vale per tutte le board tranne `OUTFIT`.

`OPTION_LABELS` (1 · Scelta Luméra, 2 · Evoluzione Naturale, 3 · Prova Qualcosa di Nuovo) è la fonte unica delle etichette dei pannelli: il backend le usa nei prompt di prova e il frontend le replica in `labels.ts`.

### 4.8 `prompts/image_templates.py`

Prompt delle prove derivati dai moduli 12–15 del Prompt Pack (`HAIR`, `HAIR_COLOR`, `EYEWEAR` v2.0; `OUTFIT` v3.0). Ogni template contiene:

1. `{{reference}}` → `REFERENCE_RULE`: "usa SOLO il pannello N della seconda immagine, ignora testo e layout, modifica la PRIMA immagine";
2. **target**: quali attributi copiare dal pannello;
3. **blocchi di preservazione** (identità, fotografia, realismo) riportati alla lettera dal Prompt Pack.

**Eccezione `OUTFIT` (v3.0):** non preserva inquadratura, posa e sfondo. Genera una foto a figura intera della stessa persona nella location `{{setting}}`. Restano preservati viso, capelli, colore dei capelli ed espressione. Il corpo viene esteso da collo e spalle con proporzioni neutre, senza snellire né idealizzare.

Location disponibili (`SETTINGS`, da tenere allineate a `Setting` in `models.py` e a `SETTING_LABEL` nel frontend):

| Valore | Descrizione |
|---|---|
| `auto` | La stessa location del pannello della board (default) |
| `restaurant` | Ristorante elegante |
| `office` | Ufficio moderno |
| `garden` | Giardino |
| `city_street` | Strada cittadina |
| `evening_event` | Evento serale |
| `cafe` | Caffè |

`build(operation, option, label, setting="auto")` restituisce `(version_tag, prompt)`.

### 4.9 API

Tutte le rotte (tranne `/api/health`) richiedono `Authorization: Bearer <token Clerk>`. Le rotte `/api/profiles` richiedono anche l'onboarding completo. Tutte le risposte sono JSON, tranne `/file`.

**`routers/users.py`** — base `/api/me`

| Metodo | Path | Body | Risposta | Note |
|---|---|---|---|---|
| `GET` | `` | — | `UserOut` | Al primo accesso crea l'utente dai dati Clerk |
| `PUT` | `` | `UserUpdate` | `UserOut` | Onboarding e modifica di nome, cognome, età. L'email è gestita da Clerk |
| `DELETE` | `` | — | 204 | Cancella tutti i dati Luméra dell'utente. L'account Clerk resta |

**`routers/profiles.py`** — base `/api/profiles`

| Metodo | Path | Body | Risposta | Note |
|---|---|---|---|---|
| `GET` | `` | — | `list[ProfileSummary]` | Profili dell'utente, dal più recente |
| `POST` | `` | multipart `photo` | `LumeraProfile` | Crea il profilo e genera la board `SEASON`. Max 15 MB |
| `POST` | `/{id}/photo` | multipart `photo` | `LumeraProfile` | Sostituisce il ritratto e rigenera la board stagione. Se esiste uno stile, rigenera anche le 4 board di stile |
| `GET` | `/{id}` | — | `LumeraProfile` | |
| `POST` | `/{id}/style` | `StyleRequest` | `LumeraProfile` | Salva la scelta e genera le 4 board di stile |
| `POST` | `/{id}/boards/{kind}/regenerate` | — | `LumeraProfile` | `kind` ∈ `SEASON, HAIR, HAIR_COLOR, OUTFIT, ACCESSORIES` |
| `POST` | `/{id}/images` | `TryOnRequest` | `ImageNode` | Una prova |
| `POST` | `/{id}/looks/{1-3}/visualize` | `LookVisualizeRequest` | `list[ImageNode]` | Catena HAIR → HAIR_COLOR → OUTFIT → (EYEWEAR), stesso pannello |
| `GET` | `/{id}/images/{image_id}/file` | — | immagine | `Cache-Control: private, immutable` |
| `POST` | `/{id}/feedback` | `FeedbackEntry` | `LumeraProfile` | Verifica che l'immagine esista e salva l'evento |

Esempio di prova:

```bash
curl -X POST http://localhost:8000/api/profiles/<id>/images \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"operation":"OUTFIT","option":2,"parent_image_id":null,"mode":"preview","setting":"garden"}'
```

### 4.10 `main.py`: gestione errori

| Eccezione | HTTP | Messaggio |
|---|---|---|
| `HTTPException` da `auth.py` | 401 / 403 | Token mancante, non valido o scaduto (401); onboarding incompleto (403) |
| `storage.NotFound` | 404 | "Profilo non trovato" (anche per i profili di altri utenti) |
| `KeyError` | 404 | messaggio dell'eccezione (es. immagine non trovata) |
| `ValueError` | 400 | messaggio dell'eccezione (precondizioni non rispettate, immagine non valida) |
| `openai.APIError` | 502 | "Errore del servizio AI: …" (stack trace nei log) |

Tutti gli errori hanno il formato `{"detail": "<messaggio in italiano>"}`, che il frontend mostra così com'è.

---

## 5. Frontend

### 5.1 Autenticazione e `App.tsx`

- `main.tsx` avvolge l'app in `ClerkProvider` (`VITE_CLERK_PUBLISHABLE_KEY`).
- `App` mostra `Landing` agli utenti non autenticati (`<Show when="signed-out">`) e `Workspace` a quelli autenticati (`<Show when="signed-in">`).
- `Workspace` registra `useAuth().getToken` in `api.ts` (`setTokenGetter`): ogni richiesta porta il token aggiornato.
- All'avvio: `GET /api/me` → se il profilo non è completo mostra `Onboarding`, altrimenti carica l'elenco dei profili e apre il più recente.

| Stato di `Workspace` | Uso |
|---|---|
| `me` | Utente corrente (`UserOut`) |
| `editingMe` | Modifica dei dati da "I miei dati" |
| `profiles` | Elenco dei profili (selettore nell'header se più di uno) |
| `profile` | `LumeraProfile` aperto |
| `loading` | Operazioni bloccanti (account, upload, stile): schermata di attesa a tutta pagina |
| `busy` | Operazioni non bloccanti (prove, rigenerazioni): overlay sull'area interessata. Il valore `board:<KIND>` identifica la board che si sta rigenerando |
| `tab` | Scheda attiva (solo con `status = styled`) |
| `currentId` | Immagine selezionata nello Studio = genitore della prossima prova |
| `mode` | `preview` o `final` per le prove |
| `setting` | Location delle prove outfit (`auto` = come nella board) |

Azioni principali:

- `saveMe`, `analyze`, `submitStyle`, `openProfile` → bloccanti;
- `tryOn`, `visualizeLook`, `regenerate` → non bloccanti. Dopo una prova il profilo viene ricaricato e la nuova immagine selezionata;
- `vote`, `save` → feedback; il profilo restituito aggiorna lo stato dei pulsanti.

**Immagini protette:** un `<img src>` non può inviare l'header `Authorization`. `api.imageSrc()` scarica l'immagine con il token e restituisce un object URL, tenuto in cache per tutta la sessione (le immagini non cambiano mai). `AuthImage` e `useImageSrc` lo usano in board, Studio e cronologia.

### 5.2 Componenti

| Componente | Responsabilità |
|---|---|
| `Landing` | Presentazione e pulsanti Registrati / Accedi (modali Clerk) |
| `Onboarding` | Nome, cognome ed età (14–120), email in sola lettura; usato al primo accesso e da "I miei dati" |
| `AuthImage` | Immagine protetta con segnaposto durante il caricamento |
| `Upload` | Drag & drop o selezione file, anteprima locale, consigli di scatto |
| `StylePicker` | 12 stili (max 2: il primo è primario, un terzo click sostituisce il secondario), preferenza sulle tendenze, occasione, comfort, testo libero |
| `Board` | Immagine della board (clic → apre a piena risoluzione), "Rigenera", e per ogni pannello: "Prova sulla foto", ♥, ✕. La board `SEASON` non ha pannelli |
| `Studio` | Immagine corrente, breadcrumb della discendenza, Annulla (vai al genitore), Salva, Scarica, qualità, selettore della location outfit, look completo 1–3, prove singole per opzione, cronologia (esclude le board) |

### 5.3 `labels.ts`

- `OPTION_LABEL`: deve restare allineato a `OPTION_LABELS` in `backend/app/prompts/boards.py`;
- `BOARD_TRYON`: quale operazione di prova usa i pannelli di ogni board;
- `STYLES` / `STYLE_IT`: valori inviati al backend (inglese) e relative etichette UI (italiano).

### 5.4 Stili

`index.css` definisce i token su `:root` (`--bg`, `--surface`, `--ink`, `--accent`, …) con la variante scura in `prefers-color-scheme: dark`. Layout responsive: Studio e hero passano a una colonna sotto 900/800px.

---

## 6. Versionamento dei prompt

- Board: `BoardPrompt.version` → `BOARD_<KIND>_V<versione>`.
- Prove: tupla `(prompt_id, version, text)` → `IMAGE_PROMPT_<OP>_V<versione>`.
- Ogni immagine salva nel database `prompt_version` e il `prompt` completo inviato (tabella `images`).

**Regola:** qualsiasi modifica al testo di un prompt richiede di aumentare la versione, così le immagini già generate restano riconducibili al prompt che le ha prodotte.

---

## 7. Come estendere

### Aggiungere una nuova board (es. `MAKEUP`)

1. `prompts/boards.py`: definire `MAKEUP = BoardPrompt("MAKEUP", "1.0", …)` usando `{option_panels}` e `{style}`; aggiungerla a `BOARDS`, a `STYLE_BOARDS` (se dipende dallo stile) e a `EXTRA_CAPTION`.
2. `models.py`: aggiungere `"MAKEUP"` a `BoardKind`.
3. Se serve una prova sulla foto:
   - `image_templates.py`: nuovo template con `{{reference}}` e blocchi di preservazione;
   - registrarlo in `TEMPLATES`;
   - aggiungere l'operazione a `TryOnOp` e `Operation` in `models.py`.
4. Frontend:
   - `types.ts`: aggiornare `BoardKind` / `TryOnOp`;
   - `labels.ts`: `BOARD_TITLE`, `BOARD_TRYON`, `OPERATION_LABEL`;
   - `App.tsx`: aggiungere la scheda;
   - `Studio.tsx`: aggiungere la voce a `GROUPS`.

### Modificare lo schema del database

1. Modificare `db_models.py`.
2. `alembic revision --autogenerate -m "…"` e rileggere la migrazione generata.
3. `alembic upgrade head`.
4. Aggiornare `models.py` / `storage.to_api()` se il dato va esposto nelle API, e `types.ts` nel frontend.

### Spostare le immagini su object storage

Tutto l'accesso ai byte passa da `storage.add_image()` e `storage.image_bytes()`: per passare a S3 o R2 basta salvare lì i byte e tenere nel DB solo la chiave dell'oggetto.

---

## 8. Test

Al momento non c'è una suite di test nel repository. La verifica è stata fatta con smoke test che usano `fastapi.testclient.TestClient` su un database SQLite temporaneo creato con Alembic, simulando Clerk e OpenAI:

```python
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///<file temporaneo>"   # prima di importare app.main
# alembic upgrade head sullo stesso URL
import app.auth as auth, app.services.generation as gen
auth.verify_token = lambda token: {"sub": "user_" + token}          # token finto = id utente
auth._fetch_clerk_user = fake_fetch                                  # dati utente finti
gen.client = lambda: SimpleNamespace(images=FakeImages())            # restituisce b64_json
```

Percorso coperto: 401 senza token, creazione dell'utente, 403 prima dell'onboarding, validazione dell'età, upload, stile, prove, look completo, feedback, rigenera, file immagine, isolamento tra due utenti (404), cancellazione dei dati. `verify_token` è stato verificato anche con token RS256 firmati localmente: valido, scaduto, firma errata, `azp` estraneo, sessione pending, algoritmo HS256.

Da aggiungere: test automatici con `pytest` sullo stesso schema, un test della migrazione su un PostgreSQL reale (la cancellazione a cascata dipende dalle FK di Postgres) e un dataset privato di ritratti per valutare a mano board e preservazione dell'identità.

---

## 9. Limiti noti

| Limite | Impatto |
|---|---|
| Nessun controllo di qualità della foto prima dell'analisi | Foto con luce scadente producono board meno affidabili; l'incertezza è affidata al titolo "Stagione probabile" generato dal modello |
| Analisi solo come pixel | Stagione e palette non sono dati strutturati: non si possono mostrare nativamente, filtrare o riusare |
| Testo nelle board generato dal modello | Possibili errori di ortografia o codici HEX imprecisi |
| Corpo generato negli outfit | Board e prove outfit sono a figura intera: tutto quello che non si vede nel ritratto (corpo, gambe, altezza) è inventato dal modello. Il prompt chiede proporzioni neutre, ma il risultato non rappresenta la corporatura reale |
| Nessuna QA automatica delle prove | Le derive di identità non vengono intercettate né ritentate |
| Chiamate sincrone lunghe | L'upload richiede ~1 board, la scelta di stile 4 board in parallelo, il look completo 4 edit in sequenza. Il proxy Vite ha un timeout di 10 minuti |
| Immagini nel database | Semplice e persistente su Railway, ma ogni immagine pesa centinaia di KB: con molti utenti conviene un object storage (§7) |
| Scritture concorrenti sullo stesso profilo | Due operazioni simultanee sullo stesso profilo (es. due rigenerazioni) possono sovrascrivere `boards` a vicenda: vince l'ultima |
| Utenti eliminati su Clerk | Non c'è ancora un webhook Clerk: se un account viene cancellato su Clerk, i dati restano nel DB finché non si chiama `DELETE /api/me` |
| Email non sincronizzata | Email, nome e cognome vengono letti da Clerk solo al primo accesso; un cambio email successivo su Clerk non viene propagato |
