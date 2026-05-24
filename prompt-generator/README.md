# 🎙️ Générateur Automatique de Prompts Audio

Plateforme full-stack de génération, optimisation et scoring de prompts professionnels pour les modèles génératifs audio (TTS, musique, SFX, voix off).

**Stack** : Python 3.11+ · FastAPI · Streamlit · SQLite · Hugging Face

---

## Prérequis

- Python 3.11+
- Un token Hugging Face avec accès aux modèles d'inférence ([huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))

---

## Installation (< 10 min)

```cmd
cd prompt-generator

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
```

Éditez `.env` et renseignez votre `HF_API_TOKEN`.

---

## Lancer l'application

**Terminal 1 — Backend API**
```cmd
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend Streamlit**
```cmd
python -m streamlit run frontend/app.py
```

> **Windows note:** If you get a "Smart App Control has blocked this file" error, always use `python -m <tool>` instead of calling the `.exe` directly. This applies to `uvicorn`, `streamlit`, `pytest`, `ruff`, etc.

- API : [http://localhost:8000](http://localhost:8000)
- Docs API (Swagger) : [http://localhost:8000/docs](http://localhost:8000/docs)
- Interface : [http://localhost:8501](http://localhost:8501)

---

## Tests

```cmd
pytest
pytest --cov=backend --cov-report=term-missing
```

---

## Structure du projet

```
prompt-generator/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── routers/                 # HTTP layer (generate, optimize, score, library, export)
│   ├── services/                # Business logic (prompt_engine, quality_scorer, hf_client)
│   ├── models/schemas.py        # Pydantic contracts
│   └── database/                # SQLite connection + CRUD
├── frontend/
│   ├── app.py                   # Streamlit entry point
│   └── pages/                   # 1_Generate, 2_Library, 3_Analytics
├── prompts/templates/           # JSON templates per audio type
├── exports/                     # Generated export files
├── tests/                       # pytest test suite
├── .env.example
└── requirements.txt
```

---

## Endpoints API

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/generate` | Générer un prompt audio |
| POST | `/api/optimize` | Optimiser un prompt existant |
| POST | `/api/score` | Scorer la qualité d'un prompt |
| GET | `/api/library` | Lister les prompts (paginé) |
| POST | `/api/library` | Sauvegarder un prompt |
| GET | `/api/library/{id}` | Détail d'un prompt |
| PUT | `/api/library/{id}` | Modifier un prompt |
| DELETE | `/api/library/{id}` | Supprimer un prompt |
| GET | `/api/library/search?q=` | Recherche full-text |
| POST | `/api/library/{id}/duplicate` | Dupliquer un prompt |
| GET | `/api/library/{id}/versions` | Historique des versions |
| POST | `/api/export` | Exporter en JSON ou Markdown |

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `HF_API_TOKEN` | Token Hugging Face **(obligatoire)** | — |
| `HF_MODEL_GENERATE` | Modèle LLM pour la génération | `mistralai/Mixtral-8x7B-Instruct-v0.1` |
| `HF_MODEL_SCORE` | Modèle pour le scoring | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `SQLITE_DB_PATH` | Chemin de la base SQLite | `./database/prompts.db` |
| `FASTAPI_PORT` | Port du backend | `8000` |
| `STREAMLIT_API_BASE_URL` | URL du backend pour Streamlit | `http://localhost:8000` |
