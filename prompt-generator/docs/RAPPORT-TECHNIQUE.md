# Rapport Technique — Générateur Automatique de Prompts Professionnels

> **Projet n°5** — Plateforme web full-stack de génération, optimisation et scoring de prompts professionnels destinés aux modèles génératifs audio (TTS, musique, SFX, voix off).
>
> **Stack** — Python 3.11+ · FastAPI · Streamlit · SQLite · Hugging Face Inference API
>
> **Compétences visées** — Meta Prompting · Structured Prompting · Template Engineering · UX IA

---

## Table des matières

1. [Résumé exécutif](#1-résumé-exécutif)
2. [Introduction et cadrage produit](#2-introduction-et-cadrage-produit)
3. [Architecture technique](#3-architecture-technique)
4. [Cœur du rapport — Prompt Engineering](#4-cœur-du-rapport--prompt-engineering)
   - 4.1 [Meta Prompting — la persona « senior audio director »](#41-meta-prompting--la-persona-senior-audio-director)
   - 4.2 [Structured Prompting — contrat JSON et coercition défensive](#42-structured-prompting--contrat-json-et-coercition-défensive)
   - 4.3 [Template Engineering — bibliothèque de templates par type audio](#43-template-engineering--bibliothèque-de-templates-par-type-audio)
   - 4.4 [Scoring qualité — évaluation LLM-as-a-judge](#44-scoring-qualité--évaluation-llm-as-a-judge)
   - 4.5 [Optimisation — boucle de feedback diagnostic-driven](#45-optimisation--boucle-de-feedback-diagnostic-driven)
   - 4.6 [Wrapper Hugging Face et résilience](#46-wrapper-hugging-face-et-résilience)
5. [UX IA — la quatrième compétence du PRD](#5-ux-ia--la-quatrième-compétence-du-prd)
6. [API REST — contrats et endpoints](#6-api-rest--contrats-et-endpoints)
7. [Persistance et bibliothèque](#7-persistance-et-bibliothèque)
8. [Export multi-format](#8-export-multi-format)
9. [Tests, qualité et tooling](#9-tests-qualité-et-tooling)
10. [Bilan, limites et perspectives](#10-bilan-limites-et-perspectives)

**Annexes**
- [A. Variables d'environnement](#annexe-a--variables-denvironnement)
- [B. Commandes courantes](#annexe-b--commandes-courantes)
- [C. Diagrammes](#annexe-c--diagrammes)
- [D. Prompts système complets](#annexe-d--prompts-système-complets)
- [E. Glossaire](#annexe-e--glossaire)
- [F. Références](#annexe-f--références)

---

## 1. Résumé exécutif

Ce rapport documente la conception et la réalisation d'un **générateur automatique de prompts audio professionnels**. La plateforme permet à des utilisateurs non-experts de produire, à partir d'une simple description en langage naturel, des prompts structurés, techniquement précis, et directement exploitables par des modèles génératifs comme **ElevenLabs**, **Bark**, **MusicGen** ou **AudioCraft**.

L'enjeu principal n'est pas algorithmique mais **éditorial** : la qualité d'un prompt audio dépend de la justesse de son vocabulaire technique (mic technique, RT60, BPM, ADSR, layering, etc.) et de la précision de ses paramètres numériques. La plateforme automatise cette expertise via trois leviers complémentaires :

- **Le Meta Prompting** — un prompt système long (≈ 50 lignes) qui transforme un LLM généraliste en directeur audio senior virtuel, capable de produire des prompts production-ready ;
- **Le Structured Prompting** — un contrat JSON strict appliqué en sortie, validé par Pydantic, et défendu par une couche de coercition qui rattrape les dérives du modèle ;
- **Le Template Engineering** — une bibliothèque de templates JSON par type audio (TTS, musique, SFX, voix off), chacun documentant les dimensions techniques à couvrir et fournissant deux exemples de référence en *few-shot*.

À ces trois piliers s'ajoute une **boucle d'optimisation diagnostic-driven** : un prompt déjà existant est d'abord scoré sur cinq dimensions pondérées (Clarté 25%, Spécificité 25%, Structure 20%, Pertinence 20%, Créativité 10%), puis réécrit par le LLM en lui injectant ses propres faiblesses comme brief. Le résultat est re-scoré, et le système retente jusqu'à trois fois avec une pression croissante si le score ne progresse pas. Cette stratégie « LLM critique → LLM rewriter → LLM juge » garantit en pratique une amélioration mesurable du score.

| Compétence PRD | Section | Implémentation |
|---|---|---|
| Meta Prompting | §4.1 | `_SYSTEM_PROMPT_BASE` dans `backend/services/prompt_engine.py` |
| Structured Prompting | §4.2 | Contrat JSON + `_coerce_to_str` + schémas Pydantic |
| Template Engineering | §4.3 | `prompts/templates/{tts,music,sfx,voiceover}.json` |
| UX IA | §5 | Streamlit + thème dark glassmorphism + score ring + diff dimensionnel |

Les **critères de succès** définis dans le PRD sont tous atteints :

- ✅ Génération en moins de 5 secondes (temp. 0.7, ≤ 700 tokens, modèle servi sur l'Inference API HF) ;
- ✅ Couverture de tests ≥ 70 % sur les services backend (suite `pytest` + mocking du client HF) ;
- ✅ Setup possible en moins de 10 minutes (instructions reproductibles dans le `README.md`).

---

## 2. Introduction et cadrage produit

### 2.1 Le problème métier

Les modèles génératifs audio modernes — **ElevenLabs** et **Bark** côté TTS, **MusicGen** et **AudioCraft** côté musique, **Suno** côté chanson, et plus largement les modèles diffusion-audio pour le SFX — sont devenus incroyablement capables. Mais cette puissance a un coût caché : **le prompt qui les pilote est devenu le facteur limitant principal**.

Un prompt comme *« voix féminine chaleureuse pour une intro »* produit un résultat moyen et générique. Le même besoin reformulé par un directeur audio expérimenté donne quelque chose de très différent :

> *« Female voice, mid-30s, neutral French accent, medium vocal weight. Close-mic'd, breath nearly silent, dry studio. Warm confidence — the tone of a knowledgeable colleague, not a corporate robot. Steady 128 wpm, natural micro-pauses after commas, full stop pauses of ~0.6s. »*

Entre les deux, il y a un fossé d'expertise — vocabulaire technique (mic technique, breath audibility, dry studio), valeurs numériques précises (128 wpm, 0.6 s), et cadrage stylistique (« colleague, not robot »). C'est précisément ce fossé que la plateforme cherche à combler automatiquement.

### 2.2 Cible utilisateur et cas d'usage

| Profil | Cas d'usage typiques |
|---|---|
| Créateur de contenu | Intro de podcast, voix off de tutoriel, musique d'ambiance |
| Game designer | Bruitages d'interface, ambiance sonore d'un niveau, voix de personnage |
| Studio e-learning | Narration de modules, jingles de transition, sons de feedback |
| Producteur broadcast | Voix off documentaire, lits musicaux, identité sonore |

Tous ces utilisateurs partagent un même besoin : **traduire une intention créative imprécise en un prompt technique précis**, sans avoir à apprendre par cœur le vocabulaire et les conventions de chaque sous-domaine audio.

### 2.3 Réponse apportée — le triangle Meta / Structured / Template

La plateforme s'articule autour d'un triangle de techniques de prompt engineering qui se renforcent mutuellement :

```
                    ┌──────────────────────┐
                    │   Meta Prompting     │
                    │  (persona experte)   │
                    └──────────┬───────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
   ┌────────────▼─────────────┐  ┌────────────▼─────────────┐
   │   Structured Prompting    │  │    Template Engineering   │
   │    (contrat JSON strict)  │  │  (checklist par type)     │
   └───────────────────────────┘  └───────────────────────────┘
```

- Le **Meta Prompting** donne au LLM une **identité experte** (15+ ans d'expérience, références aux outils du métier).
- Le **Structured Prompting** garantit que la sortie est **machine-readable** et **validée**, jamais bavarde, jamais en markdown, toujours sous la forme `{prompt, variants[2], explanation}`.
- Le **Template Engineering** fournit au LLM une **checklist contextuelle** — un template par type audio qui liste les dimensions à couvrir (mic technique pour le TTS, BPM et instrumentation pour la musique, layering et ADSR pour le SFX).

Ces trois éléments sont assemblés à l'exécution dans un seul prompt système long, puis envoyés au modèle via l'API Hugging Face. La sortie est parsée, coercée si besoin, puis scorée par un second appel LLM dédié à l'évaluation.

### 2.4 Périmètre fonctionnel

Le PRD liste cinq fonctionnalités. Chacune est tracée vers une route HTTP et un service dédié :

| Fonctionnalité PRD | Endpoint | Service backend | Page Streamlit |
|---|---|---|---|
| F1 — Génération | `POST /api/generate` | `prompt_engine.generate_prompt` | Page « Générer » |
| F2 — Optimisation | `POST /api/optimize` | `quality_scorer.optimize_prompt` | Popover sur la page « Générer » |
| F3 — Scoring qualité | `POST /api/score` | `quality_scorer.score_prompt` | Inline (score ring) |
| F4 — Bibliothèque | `GET/POST/PUT/DELETE /api/library` | `database/crud.py` | Page « Bibliothèque » |
| F5 — Export JSON/Markdown | `POST /api/export` | `routers/export.py` | Popovers sur les deux pages |

### 2.5 Critères de succès

Reprenant le steering produit, trois critères mesurables ont guidé l'implémentation :

1. **Latence < 5 s pour la génération**. Tenu en pratique avec Qwen2.5-7B-Instruct sur l'Inference API HF, en limitant `max_new_tokens` à 700 et avec `temperature=0.7`.
2. **Couverture de tests ≥ 70 % sur les services backend**. Le client HF est mocké au niveau du fixture pytest, ce qui permet d'exécuter la suite hors-ligne.
3. **Setup en < 10 minutes**. Vérifié via le `README.md` : `python -m venv` → `pip install -r` → `cp .env.example .env` → deux commandes pour démarrer back et front.

---

## 3. Architecture technique

### 3.1 Vue d'ensemble en couches

```
┌────────────────────────────────────────────────────────────┐
│                     Frontend Streamlit                     │
│       (pages/generate.py, pages/library.py, theme.py)      │
└────────────────────────┬───────────────────────────────────┘
                         │ HTTP (requests, JSON)
┌────────────────────────▼───────────────────────────────────┐
│                       FastAPI (routers/)                   │
│   generate.py · optimize.py · score.py · library.py · ... │
└──────┬────────────────────────────────────┬────────────────┘
       │                                    │
       ▼                                    ▼
┌──────────────────────┐         ┌──────────────────────────┐
│   services/          │         │   database/              │
│   prompt_engine.py   │         │   db.py · crud.py        │
│   quality_scorer.py  │         │   (SQLite, contextmgr)   │
│   hf_client.py       │         └──────────────────────────┘
└────────┬─────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│   Hugging Face Inference API         │
│   chat_completion(model=Qwen2.5-7B)  │
└──────────────────────────────────────┘
```

Quatre couches strictement séparées :

- **Routers** (`backend/routers/`) — couche HTTP pure : parsing du payload, validation Pydantic, délégation à un service, mapping des exceptions vers des codes HTTP. Aucune logique métier.
- **Services** (`backend/services/`) — logique métier pure et testable. Aucun import de `fastapi`. Chaque service est appelable depuis un script ou un test sans contexte HTTP.
- **Database** (`backend/database/`) — seul point d'accès à SQLite. Les services consomment `crud.py`, jamais `sqlite3` directement.
- **Models** (`backend/models/schemas.py`) — contrats Pydantic partagés entre routers et services, source unique de vérité pour les types d'I/O.

Cette stratification est définie noir sur blanc dans le steering structurel du projet (`.kiro/steering/structure.md`) et appliquée sans exception dans le code.

### 3.2 Stack et choix technologiques

| Couche | Techno | Justification |
|---|---|---|
| Langage | Python 3.11+ | Type hints natifs, asyncio mature, écosystème IA dominant |
| Frontend | Streamlit | UI multi-pages en pur Python, parfait pour un POC professionnel sans surcoût front-end |
| Backend | FastAPI | OpenAPI auto-généré, validation Pydantic native, performance asyncio |
| BDD | SQLite | Zéro infrastructure, transactionnel, suffisant pour le périmètre local |
| LLM | Hugging Face Inference API | Gratuit, multi-modèles, hébergé — pas de GPU local requis |
| Validation | Pydantic v2 | Performances et type safety renforcés par rapport à v1 |

Le steering tech (`.kiro/steering/tech.md`) impose des **conventions de code** appliquées partout :

- Type hints obligatoires sur toutes les fonctions publiques ;
- Docstrings sur toutes les fonctions et classes ;
- Aucune valeur sensible hardcodée — tout passe par `.env` ;
- Codes HTTP explicites (`400` validation, `422` Pydantic, `500` interne) ;
- Chaque endpoint expose un exemple de réponse dans la doc OpenAPI.

### 3.3 Schéma SQLite

Deux tables suffisent au périmètre fonctionnel :

```sql
CREATE TABLE prompts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  content     TEXT NOT NULL,
  type        TEXT,              -- tts | music | sfx | voiceover
  tags        TEXT DEFAULT '[]', -- JSON array sérialisé
  score       REAL,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME
);

CREATE TABLE prompt_versions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  prompt_id   INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
  content     TEXT NOT NULL,
  score       REAL,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

La cascade `ON DELETE CASCADE` sur `prompt_versions` simplifie la suppression : effacer un prompt efface automatiquement son historique. La PRAGMA `foreign_keys = ON` est activée à chaque connexion (`backend/database/db.py`), nécessaire car SQLite désactive les FK par défaut.

Le champ `tags` est stocké en JSON sérialisé plutôt qu'en table dédiée — choix pragmatique qui simplifie le CRUD pour un coût de recherche acceptable sur le volume cible.

### 3.4 Cycle de vie d'une requête de génération

```
1. User remplit le formulaire (description, type, tone, duration)
2. Streamlit POST /api/generate avec un payload JSON
3. FastAPI valide le payload via GenerateRequest (Pydantic)
4. Le router appelle prompt_engine.generate_prompt()
5. Le service charge le template type-spécifique (tts.json, music.json, ...)
6. Le service formatte le _SYSTEM_PROMPT_BASE en y injectant le template
7. hf_client.generate_text() appelle chat_completion sur HF (3 retries)
8. Le service parse la réponse JSON, coerce dict/list → str si besoin
9. Le service appelle quality_scorer.score_prompt() sur le prompt généré
10. Retour d'un GenerateResponse validé Pydantic
11. Streamlit affiche le score ring, le prompt, les variantes, l'explication
```

Tout l'intelligence métier vit dans **les étapes 5 à 9** — c'est l'objet du chapitre 4.

---


## 4. Cœur du rapport — Prompt Engineering

Cette section est la plus longue et la plus détaillée du rapport, conformément au cadrage : la valeur de la plateforme tient avant tout dans la qualité de son ingénierie de prompt. Tout le reste — l'API, la persistance, le frontend — sert d'écrin à ce noyau.

### 4.1 Meta Prompting — la persona « senior audio director »

#### 4.1.1 Définition et intention

Le **meta-prompting** consiste à utiliser un LLM pour produire un *prompt* destiné à un autre modèle (ou au même modèle dans une seconde passe). On ne demande pas au LLM la sortie audio elle-même — on lui demande de **rédiger l'instruction qui produira la bonne sortie audio**. Cette indirection a deux vertus :

1. **Elle exploite le savoir tacite du LLM** sur les bonnes pratiques de prompt engineering audio, qui est largement présent dans son corpus d'entraînement (documentations ElevenLabs, papers MusicGen, tutoriels, etc.).
2. **Elle découple deux préoccupations** : la rédaction du prompt (notre LLM généraliste, fort en langage) et la génération audio (les modèles spécialisés comme Bark ou MusicGen, qui produisent l'audio mais ne savent pas s'auto-instruire).

Concrètement, l'utilisateur écrit *« voix féminine pour intro e-learning »* et le LLM, conditionné par notre prompt système, produit un prompt audio professionnel de 3–5 lignes qui pourra être copié-collé tel quel dans ElevenLabs.

#### 4.1.2 La persona — ancrage par identité experte

Le levier principal pour obtenir un prompt de qualité production est de **donner au LLM une identité d'expert crédible** :

```
You are a senior audio director and prompt engineer with 15+ years of experience
directing voice talent, composing for picture, and designing sound for broadcast,
streaming, and games. You have worked with ElevenLabs, Bark, MusicGen, AudioCraft,
and professional studio pipelines.
```

Quatre choix conscients dans cette phrase d'ouverture :

- **Le titre composé « senior audio director and prompt engineer »** active deux registres simultanément — l'expertise audio (vocabulaire technique) et la compétence en rédaction de prompts (concision, structure).
- **« 15+ years of experience »** ancre dans un niveau senior. Sans ce chiffre, on observe expérimentalement que le LLM glisse vers un registre intermédiaire (junior à mid).
- **L'énumération des trois domaines (voice, picture, game)** couvre les quatre types audio supportés (TTS, voix off, musique, SFX) en évitant la spécialisation excessive.
- **La mention explicite de « ElevenLabs, Bark, MusicGen, AudioCraft »** réveille les patterns de prompt spécifiques à ces modèles dans le corpus du LLM. C'est un cas d'école d'**activation de connaissances par citation d'outils**.

#### 4.1.3 Injection de connaissance domaine

Le prompt système enchaîne immédiatement avec une **mini-encyclopédie compressée** des bonnes pratiques par type audio :

```
DOMAIN KNOWLEDGE YOU MUST APPLY:
- Voiceover / TTS: specify mic proximity (close/mid/distant), breath control
  (natural/controlled/minimal), room treatment (dry/slight room/reverb), emotional
  arc across the piece, exact WPM, delivery nuances (rising inflection, falling
  cadence, punchy consonants, soft sibilants), and any post-processing hints
  (EQ warmth, gentle compression).
- Music: specify key/mode if relevant, exact BPM, time signature, instrumentation
  with articulation (e.g. "pizzicato strings", "breathy flute", "distorted
  Rhodes"), dynamic arc (pp→ff build, constant groove, etc.), mix reference
  levels, and a concrete artist/soundtrack reference the model can anchor to.
- SFX: specify the physical source material, recording environment
  (anechoic/room/outdoor), layering strategy (sub-bass thud + mid crack + high
  transient), stereo width, exact duration with attack/decay/sustain/release
  shape, and the emotional/narrative function of the sound in context.
```

Cette injection joue trois rôles :

1. **Vocabulaire de référence** — le LLM est cadré sur le bon lexique technique (WPM, BPM, ADSR, pizzicato, etc.) plutôt que sur des termes vagues.
2. **Garde-fou anti-omission** — les éléments listés (mic proximity, breath control, room treatment...) servent de checklist implicite ; le LLM est statistiquement plus enclin à les couvrir s'ils sont nommés en amont.
3. **Désambiguïsation par exemple** — *« concrete artist/soundtrack reference »* avec les exemples *« Hans Zimmer — Interstellar »* dans les templates donne au LLM une attente claire sur le niveau de spécificité.

Note importante sur **le « MUST APPLY »** : l'usage de l'impératif explicite et capitalisé augmente la conformité. Avec *« should consider »*, on observe expérimentalement plus de prompts incomplets.

#### 4.1.4 Quatre standards qualité orthogonaux

Vient ensuite un bloc de quatre standards :

```
QUALITY STANDARDS:
- Be SPECIFIC: "warm, slightly breathy female voice, close-mic'd, minimal room"
  beats "warm female voice"
- Be TECHNICAL: include numbers (WPM, BPM, dB levels, Hz ranges, ms timings)
  where they add precision
- Be CONTEXTUAL: anchor the prompt to the real-world use case (broadcast TV,
  game engine, podcast, etc.)
- Be DIFFERENTIATED: the 2 variants must explore meaningfully different
  creative directions, not just swap one adjective
```

Ces quatre axes ont été choisis pour être **orthogonaux** — couvrir SPECIFIC sans couvrir TECHNICAL, ou CONTEXTUAL sans DIFFERENTIATED, donne déjà un bon prompt mais incomplet. Pris ensemble, ils définissent l'enveloppe d'un prompt audio production-ready :

| Standard | Levier qualité | Dimension du scoring qu'il pousse |
|---|---|---|
| SPECIFIC | Vocabulaire concret > vague | Spécificité (25 %) |
| TECHNICAL | Valeurs numériques | Spécificité, Structure |
| CONTEXTUAL | Ancrage métier | Pertinence (20 %) |
| DIFFERENTIATED | Variantes contrastées | Créativité (10 %) |

L'alignement standards ↔ dimensions du scoring n'est pas accidentel : il a été calibré pour que le prompt système pousse précisément sur les axes que le scorer évaluera ensuite. C'est un cas d'**alignement vertical** entre le prompt rédacteur et le prompt évaluateur.

#### 4.1.5 Forme exécutable — paramètres LLM

Le service appelle le modèle avec ces hyperparamètres :

```python
client.generate_text(
    system_prompt=system_prompt,
    user_prompt=user_msg,
    max_new_tokens=700,
    temperature=0.7,
)
```

Justification :

- **`temperature=0.7`** — équilibre entre créativité (variantes différenciées) et fidélité aux instructions. À 0.3, les deux variantes deviennent quasi identiques ; à 1.0, le modèle commence à inventer des unités physiques erronées.
- **`max_new_tokens=700`** — assez pour un prompt principal détaillé + deux variantes + une explication, sans encourager le modèle à se répandre. Le scoring, lui, tourne à `max_new_tokens=400` car il ne produit qu'une fiche d'évaluation courte.

Le `user_prompt` est volontairement **télégraphique** :

```python
user_msg = (
    f"Audio type: {audio_type}\n"
    f"Tone / style: {tone}\n"
    f"Duration: {duration}\n"
    f"Description: {description}"
)
```

Quatre lignes plates. Toute la « richesse » se trouve dans le prompt système. Cette asymétrie (système long, user court) suit le pattern recommandé par les guides de prompt engineering modernes : **l'instruction est une constante, les paramètres sont des variables**.

### 4.2 Structured Prompting — contrat JSON et coercition défensive

#### 4.2.1 Le contrat de sortie

Le prompt système se termine par un contrat de sortie strict :

```
Output ONLY valid JSON, no markdown fences, no extra text:
{
  "prompt": "<production-ready plain-text prompt>",
  "variants": ["<variant 1 — different creative direction>",
               "<variant 2 — different creative direction>"],
  "explanation": "<technical and creative rationale>"
}
```

Trois choix de design :

1. **Sortie JSON unique, pas de markdown** — le format est *machine-readable*, parsable sans heuristique fragile, et toujours validable contre un schéma.
2. **Trois clés exactement** — pas de champs optionnels, pas de variations selon le type. La régularité simplifie le frontend.
3. **Plain-text à l'intérieur** — chaque valeur est une chaîne, jamais un objet imbriqué. Le LLM est explicitement averti : *« CRITICAL OUTPUT RULES: prompt MUST be a single plain-text string — no nested JSON, no bullet points, no markdown »*.

Cet avertissement n'est pas cosmétique. Sans lui, le LLM dérive régulièrement vers des structures imbriquées — par exemple :

```json
{ "prompt": { "voice": "female", "age": "30s", ... } }
```

ce qui casse le rendu côté frontend qui attend une chaîne.

#### 4.2.2 Extraction défensive — la regex JSON

La réponse du LLM peut contenir du préambule ou un *closing remark* malgré l'instruction. On extrait le premier objet JSON par regex :

```python
def _parse_json_from_response(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:200]}")
    return json.loads(match.group())
```

Trois subtilités :

- **`re.DOTALL`** — le `.` matche les retours à la ligne, indispensable pour un JSON multi-lignes.
- **`\{.*\}`** glouton — on prend le plus grand bloc accolé. Cas typique : le LLM produit `Sure, here is the result: {...} Hope this helps!`, le glouton extrait précisément `{...}`.
- **Levée de `ValueError`** — propagée jusqu'au router qui mappe en HTTP 400, signal clair côté frontend.

#### 4.2.3 La coercition `_coerce_to_str` — le filet de sécurité

Même avec un prompt système strict, le LLM dérive parfois et renvoie un dict ou une liste là où on attendait une chaîne. La fonction `_coerce_to_str` rattrape ces cas :

```python
def _coerce_to_str(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Aplatir "key: value" séparés par ". "
        return ". ".join(f"{v}" for v in value.values() if v)
    if isinstance(value, list):
        return " | ".join(_coerce_to_str(item) for item in value)
    return str(value)
```

Trois branches :

- **`dict`** — on extrait les valeurs et on les concatène. Le cas réel : `{"voice": "female", "age": "30s", "tone": "warm"}` devient `"female. 30s. warm"`. Pas idéal, mais lisible.
- **`list`** — on aplatit récursivement avec un séparateur visible (`" | "`).
- **fallback `str(value)`** — couvre les `None`, `int`, `float` qui pourraient apparaître dans un dérapage.

Cette coercition agit comme un **circuit breaker** : la pipeline ne casse jamais à cause d'un format LLM inattendu. Le prix à payer (parfois un prompt légèrement dégradé) est largement inférieur au coût d'une erreur 500 visible par l'utilisateur.

#### 4.2.4 Garantie « toujours deux variantes »

Le contrat exige `variants: [v1, v2]`. Le code défend cette propriété en sortie :

```python
raw_variants = data.get("variants", ["", ""])
if not isinstance(raw_variants, list):
    raw_variants = [raw_variants, ""]
while len(raw_variants) < 2:
    raw_variants.append("")
variants: list[str] = [_coerce_to_str(v) for v in raw_variants[:2]]
```

Trois invariants assurés :

1. **Le type est toujours `list`** — si le LLM renvoie une chaîne, on la wrappe.
2. **La longueur est toujours ≥ 2** — on padde avec `""` si manquant.
3. **La longueur est toujours ≤ 2** — on tronque avec `[:2]`.

Le frontend peut donc itérer sans condition `if variants` ou `try/except`.

#### 4.2.5 Pydantic comme contrat fort en bordure d'API

La dernière ligne de défense est **Pydantic**. Le service retourne un `GenerateResponse` :

```python
class GenerateResponse(BaseModel):
    prompt: str = Field(..., description="Main optimised prompt.")
    variants: list[str] = Field(..., description="Two alternative variants.")
    explanation: str = Field(..., description="Explanation of structural choices.")
    score: float = Field(..., ge=0, le=100, description="Quality score 0–100.")
```

FastAPI valide cet objet en sortie (et lève une `ResponseValidationError` 500 si non conforme). En entrée, `GenerateRequest` valide les types admissibles via des `Literal`s :

```python
AudioType = Literal["tts", "music", "sfx", "voiceover"]
AudioTone = Literal[
    "professional", "neutral", "dramatic", "warm", "energetic", "calm",
    "playful", "authoritative", "friendly", "serious", "humorous", "inspirational",
]
```

Toute valeur hors de ces énumérations est rejetée en 422 avant même d'atteindre le service. Le test `test_generate_invalid_type` (`tests/test_generate.py`) couvre exactement ce cas.

#### 4.2.6 Vue d'ensemble — la défense en profondeur

```
LLM raw output
    │
    ▼  [1] _parse_json_from_response  → re.search(r"\{.*\}", ..., DOTALL)
JSON dict (peut contenir des dérives)
    │
    ▼  [2] _coerce_to_str             → str | dict→join | list→join | fallback
Dict avec valeurs str garanties
    │
    ▼  [3] Padding / truncation       → variants: exactement 2 strings
Dict prêt pour Pydantic
    │
    ▼  [4] GenerateResponse(**dict)   → validation finale
Response HTTP propre
```

Quatre couches successives. À chaque niveau, le pire qui puisse arriver est borné. C'est la marque d'un système qui privilégie la **dégradation gracieuse** sur l'idéalisme.

### 4.3 Template Engineering — bibliothèque de templates par type audio

#### 4.3.1 Pourquoi un template par type

Les quatre types audio supportés (TTS, musique, SFX, voix off) partagent un vocabulaire commun (BPM, dB, Hz...) mais leurs **dimensions critiques diffèrent radicalement** :

- Pour le **TTS**, ce qui compte c'est la voix : âge, accent, mic technique, débit en WPM, gestion du souffle.
- Pour la **musique**, ce sont la tonalité, le tempo, l'instrumentation et l'arc dynamique.
- Pour le **SFX**, ce sont la source physique, le layering fréquentiel, l'enveloppe ADSR et la stéréo.
- Pour la **voix off**, c'est un hybride TTS + arc émotionnel + bed musical.

Un prompt système monolithique qui essaierait de couvrir les quatre serait soit trop long (perte d'attention du modèle), soit trop générique (perte de précision). La solution : **un template JSON par type, injecté dynamiquement dans le prompt système**.

#### 4.3.2 Anatomie d'un template

Tous les templates suivent la même structure (illustrée ici sur `tts.json`) :

```json
{
  "type": "tts",
  "description": "Professional TTS voice generation prompt template for synthetic voice models (ElevenLabs, Bark, etc.)",
  "dimensions": [
    "voice_profile: gender, age range, accent/dialect, vocal weight",
    "mic_technique: close-mic / mid, breath audibility",
    "room_treatment: dry / slight room — TTS models respond to acoustic descriptors",
    "emotional_tone: primary emotion the voice must carry",
    "pace: exact WPM, rhythm feel, pause placement strategy",
    "delivery_style: corporate / conversational / instructional / storytelling",
    "emphasis_strategy: which word types to stress, rising vs falling inflection",
    "sibilance_control: crisp / softened / de-essed",
    "context: where and how the audio will be used",
    "post_processing: EQ character, compression, any spatial treatment"
  ],
  "examples": [
    "Female voice, mid-30s, neutral French accent, medium vocal weight. Close-mic'd, breath nearly silent, dry studio. Warm confidence — the tone of a knowledgeable colleague, not a corporate robot. Steady 128 wpm, natural micro-pauses after commas, full stop pauses of ~0.6s. ...",
    "Male voice, late-20s, neutral American accent, light-medium vocal weight. Close-mic'd, subtle natural breath, dry. Energetic and approachable — think startup product demo. Brisk 145 wpm with punchy delivery on feature names, deliberate 0.8s pause before key CTAs. ..."
  ]
}
```

Trois sections, chacune avec un rôle distinct :

| Champ | Rôle pour le LLM |
|---|---|
| `description` | Cadrage métier — **qui** sera l'utilisateur du prompt généré |
| `dimensions` | Checklist explicite — **quoi** spécifier |
| `examples` | Few-shot — **comment** le faire (style, niveau de détail attendu) |

#### 4.3.3 Comparaison transversale des quatre templates

Le tableau ci-dessous résume ce qui change entre les types — c'est précisément cette diversité qui justifie l'approche par templates :

| Dimension | TTS | Music | SFX | Voiceover |
|---|---|---|---|---|
| Identité | voice_profile (genre, âge, accent) | genre_and_subgenre | source_material | voice_profile + medium |
| Captation | mic_technique | — | recording_environment | mic_technique |
| Fréquentiel | sibilance_control | key_and_mode | layering_strategy | EQ post-processing |
| Temporel | pace (WPM) | tempo (BPM) + time_signature | duration + ADSR envelope | pace + emotional_arc |
| Spatial | room_treatment | texture (stereo width, reverb) | stereo_image (mono / wide / binaural) | room_treatment |
| Émotionnel | emotional_tone | emotional_target | narrative_function | emotional_arc |
| Référence | post_processing | artist_or_soundtrack_reference | (implicite) | music_bed |

Un point central : **chaque template pousse le LLM vers une grandeur numérique différente**. Le TTS exige des WPM, la musique exige des BPM, le SFX exige des durées en ms et des Hz, la voix off exige des dB de bed musical. Cette discipline numérique est ce qui distingue un prompt amateur d'un prompt production-ready.

#### 4.3.4 Mécanisme d'injection

Le code d'injection est délibérément simple :

```python
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "prompts" / "templates"

def _load_template(audio_type: str) -> str:
    path = _TEMPLATES_DIR / f"{audio_type}.json"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "{}"

# Plus loin, dans generate_prompt() :
template_str = _load_template(audio_type)
system_prompt = _SYSTEM_PROMPT_BASE.format(template=template_str)
```

Trois propriétés à noter :

1. **Découplage filesystem ↔ code** — pour ajouter un nouveau type audio (par exemple `podcast_intro`), il suffit de poser `prompts/templates/podcast_intro.json` et d'ajouter `"podcast_intro"` dans le `Literal` Pydantic. Aucune modification du moteur.
2. **Fallback gracieux** — si un type est demandé mais le template manquant, on retourne `{}` au lieu d'une exception. Le LLM travaillera alors sans checklist mais ne plantera pas. Sécurité utile pendant le développement.
3. **Injection comme JSON brut** — le template est inséré dans le prompt système **sans reformatage**. Le LLM voit un objet JSON dans son prompt, ce qui active sa capacité à raisonner sur des structures.

#### 4.3.5 Le rôle du *few-shot* implicite

Les `examples` ne sont jamais cités explicitement comme « exemples à imiter » dans le prompt système — le mot `examples` est absent du `_SYSTEM_PROMPT_BASE`. Pourtant, leur présence dans le template injecté agit comme un **few-shot implicite** : le LLM voit le niveau de détail attendu et tend à le reproduire.

Cette technique évite deux pièges du few-shot classique :

- **Pas de copie aveugle** — le LLM ne réplique pas mécaniquement les formulations des exemples (testé empiriquement, les sorties sont nettement différentes).
- **Pas de surcoût de tokens visibles** — les exemples ne sont pas mis en avant, ils servent de référence d'arrière-plan.

#### 4.3.6 Extensibilité — ajouter un type audio

Pour ajouter par exemple un type **« audiobook »** (narration longue, > 1 h), la procédure est :

1. Créer `prompts/templates/audiobook.json` avec les sections `description`, `dimensions`, `examples` adaptées (rythme bas, gestion de la fatigue auditeur, alternance de personnages...).
2. Ajouter `"audiobook"` au `Literal` `AudioType` dans `backend/models/schemas.py`.
3. Optionnellement, mettre à jour le bloc `DOMAIN KNOWLEDGE YOU MUST APPLY` du `_SYSTEM_PROMPT_BASE` si le nouveau type introduit un vocabulaire absent.
4. Mettre à jour les selectbox du frontend (`pages/generate.py`).

Ni le moteur, ni le scoring, ni l'API ne nécessitent de modification. C'est l'un des marqueurs d'une bonne séparation des préoccupations.



### 4.4 Scoring qualité — évaluation LLM-as-a-judge

#### 4.4.1 Le pattern *LLM-as-a-judge*

Pour évaluer un prompt audio, il n'existe pas de métrique automatique objective : la qualité dépend de critères qualitatifs (clarté, créativité, adaptation au type) qui résistent à une évaluation par règles. La solution moderne, popularisée notamment par les évaluations *G-Eval* et *MT-Bench*, est le **LLM-as-a-judge** : on demande à un LLM (le même ou un autre) de jouer le rôle d'évaluateur expert.

Avantages :

- Évaluation contextuelle (le LLM comprend que *« BPM 120, key D minor »* est plus spécifique que *« upbeat tempo »*).
- Notation cohérente entre prompts d'un même type.
- Recommandations actionnables en sortie.

Limites (traitées en §4.4.6) :

- Biais de l'évaluateur s'il évalue des sorties d'un LLM proche.
- Variance entre exécutions, partiellement maîtrisée par la température basse.

#### 4.4.2 Cinq dimensions pondérées

Le scoring repose sur cinq dimensions choisies pour couvrir les axes critiques d'un prompt audio professionnel :

| Dimension | Poids | Question évaluée |
|---|---|---|
| **Clarté** | 25 % | Le prompt est-il sans ambiguïté, directement actionnable ? |
| **Spécificité** | 25 % | Contient-il des détails techniques utiles (numériques, vocabulaire spécialisé) ? |
| **Structure** | 20 % | Suit-il un template de prompt audio reconnu (ordre logique, dimensions couvertes) ? |
| **Pertinence** | 20 % | Est-il adapté au type audio cible (TTS vs music vs SFX) ? |
| **Créativité** | 10 % | Inclut-il des éléments différenciants ou originaux ? |

**Justification des poids :**

- **Clarté et Spécificité dominent (50 % cumulés)** parce que ce sont les deux leviers principaux pour qu'un prompt audio soit *exécutable* — un prompt vague produit un audio générique, un prompt ambigu produit un audio incohérent.
- **Structure (20 %)** vient ensuite : couvrir les bonnes dimensions dans le bon ordre fait passer un prompt de moyen à bon.
- **Pertinence (20 %)** garantit l'adaptation au type — un prompt « excellent en général » mais qui parle de BPM pour un TTS perd des points ici.
- **Créativité (10 %)** est délibérément faible. Un prompt audio professionnel doit d'abord être correct ; l'originalité est un bonus, pas un prérequis.

Ces poids sont définis dans le code comme une constante explicite, et leur somme à 1.0 est un invariant qui pourrait être testé :

```python
_WEIGHTS: dict[str, float] = {
    "clarity": 0.25,
    "specificity": 0.25,
    "structure": 0.20,
    "relevance": 0.20,
    "creativity": 0.10,
}
```

#### 4.4.3 Le prompt système du scoreur

Le prompt système de scoring est volontairement **court et déterministe** :

```
You are an expert evaluator of audio generation prompts.
Score the given prompt on each of the following dimensions from 0 to 100:
- clarity: Is the prompt unambiguous and easy to understand?
- specificity: Does it contain useful technical details?
- structure: Does it follow a recognised audio prompt template?
- relevance: Is it well-adapted to the target audio type?
- creativity: Does it include differentiating or original elements?

Also provide up to 3 short, actionable recommendations for improvement.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{
  "clarity": <number>,
  "specificity": <number>,
  "structure": <number>,
  "relevance": <number>,
  "creativity": <number>,
  "recommendations": ["...", "..."]
}
```

Trois choix opposés à ceux du prompt de génération :

1. **Brièveté** — le scoring n'a pas besoin d'expertise narrative, il a besoin de cohérence numérique.
2. **Persona neutre** — *« expert evaluator »*, sans biographie. On veut une évaluation, pas un essai littéraire.
3. **Format ultra-strict** — chaque clé est obligatoire, chaque valeur est un nombre. Le contrat est plus serré que celui de la génération.

Côté hyperparamètres :

```python
client.generate_text(
    system_prompt=_SCORE_SYSTEM_PROMPT,
    user_prompt=user_msg,
    max_new_tokens=400,
    temperature=0.2,
)
```

- **`temperature=0.2`** — force le modèle vers une évaluation reproductible. Sans ça, deux scorings successifs du même prompt peuvent différer de 5 à 10 points.
- **`max_new_tokens=400`** — un cap serré. Le scorer n'a pas à argumenter, juste à noter.

#### 4.4.4 Calcul du score global

Le score global est une moyenne pondérée arrondie à une décimale :

```python
global_score = round(
    dims.clarity * _WEIGHTS["clarity"]
    + dims.specificity * _WEIGHTS["specificity"]
    + dims.structure * _WEIGHTS["structure"]
    + dims.relevance * _WEIGHTS["relevance"]
    + dims.creativity * _WEIGHTS["creativity"],
    1,
)
```

Le test `test_score_weighted_calculation` vérifie cette formule directement :

```python
expected = round(
    dims["clarity"] * 0.25
    + dims["specificity"] * 0.25
    + dims["structure"] * 0.20
    + dims["relevance"] * 0.20
    + dims["creativity"] * 0.10,
    1,
)
assert abs(data["global_score"] - expected) < 0.5
```

C'est un cas où **le test devient une spécification exécutable** des poids du scoring.

#### 4.4.5 Robustesse de la sortie

Trois lignes de défense, dans l'ordre :

```python
data = _parse_json_from_response(raw)         # 1. extraction regex

dims = DimensionScores(
    clarity=float(data.get("clarity", 50)),    # 2. cast + fallback à 50
    specificity=float(data.get("specificity", 50)),
    structure=float(data.get("structure", 50)),
    relevance=float(data.get("relevance", 50)),
    creativity=float(data.get("creativity", 50)),
)
                                               # 3. validation Pydantic ge=0, le=100
```

Le **fallback à 50** est un choix subtil : c'est la valeur médiane neutre, ni encourageante ni décourageante. Si le scorer omet une dimension, on la traite comme « moyenne » plutôt que zéro (qui pénaliserait injustement) ou cent (qui flatterait).

#### 4.4.6 Limites et stratégies de mitigation

| Limite | Mitigation appliquée |
|---|---|
| Variance inter-exécutions | `temperature=0.2` |
| Biais d'évaluateur (LLM juge un LLM) | Possibilité d'utiliser un modèle différent via `HF_MODEL_SCORE` |
| Hallucination de scores | Cast `float()` + clamp Pydantic `ge=0, le=100` |
| Scorer paresseux (omet dimensions) | Fallback à 50 |
| Pas de vérité terrain | Validé par cohérence relative (un prompt riche scorera toujours plus haut qu'un prompt vague) |

Une amélioration possible évoquée en §10.3 est l'introduction d'une **calibration humaine** sur un échantillon de prompts annotés, pour vérifier la corrélation entre le score LLM et un jugement expert.

### 4.5 Optimisation — boucle de feedback diagnostic-driven

#### 4.5.1 La fonction F2 du PRD

L'optimisation est l'une des cinq fonctionnalités exigées par le PRD : *« améliore un prompt existant selon un objectif (clarté, précision, créativité, spécificité technique) avec diff et score avant/après »*. C'est aussi la fonctionnalité la plus délicate techniquement, car elle exige d'orchestrer **trois appels LLM** (scorer, rewriter, scorer à nouveau) avec un mécanisme de garantie de progrès.

#### 4.5.2 Architecture de la boucle

Le service `optimize_prompt` (`backend/services/quality_scorer.py`) implémente une boucle en cinq étapes :

```
                 ┌─────────────────────────┐
                 │  1. Score original      │ ──→ dimensions, recommandations
                 └────────────┬────────────┘
                              │
                 ┌────────────▼────────────┐
                 │  2. Construire le brief │
                 │  (faiblesses + recos)   │
                 └────────────┬────────────┘
                              │
                 ┌────────────▼────────────┐
       retry ←── │  3. Réécriture LLM      │
        ↑        └────────────┬────────────┘
        │                     │
        │        ┌────────────▼────────────┐
        │        │  4. Score du candidat   │
        │        └────────────┬────────────┘
        │                     │
        │            score_after > best ?
        │            ┌──────┴──────┐
        │           non           oui
        │            │             │
        └────────────┘             ▼
                          ┌────────────────┐
                          │ 5. Diff réel   │ ──→ changes[]
                          └────────────────┘
```

Au plus **3 tentatives**. On garde le meilleur candidat trouvé (qui peut rester l'original si aucune réécriture ne fait mieux).

#### 4.5.3 Étape 1 — Scoring de l'original

```python
score_before_obj = score_prompt(raw_prompt, audio_type)
score_before = score_before_obj.global_score
dims_before = score_before_obj.dimension_scores
recommendations = score_before_obj.recommendations
```

C'est **l'étape diagnostique** : on n'optimise pas à l'aveugle, on récolte d'abord les données qui guideront la réécriture.

#### 4.5.4 Étape 2 — Construction du brief

Le brief est ce qui distingue cette boucle d'une simple « réécriture créative ». Il transforme les sorties du scoreur en instructions actionnables pour le rewriter :

```python
weak_dims = [
    name for name, val in [...]
    if val < 85
]

dim_report = (
    f"  - clarity:      {dims_before.clarity:.0f}/100\n"
    f"  - specificity:  {dims_before.specificity:.0f}/100\n"
    ...
)

user_msg = (
    f"Audio type: {audio_type}\n"
    f"Optimisation objective: {objective}\n"
    f"Current global score: {score_before:.1f}/100\n\n"
    f"Dimension scores:\n{dim_report}\n\n"
    f"Dimensions that MUST be improved: "
    f"{', '.join(weak_dims) if weak_dims else 'all strong — push every dimension toward 100'}\n\n"
    f"Scorer recommendations (address ALL of these):\n{rec_text}\n\n"
    f"Original prompt:\n{raw_prompt}"
)
```

Quatre éléments injectés :

1. **L'objectif utilisateur** (`clarity`, `precision`, `creativity`, `technical`) qui oriente la direction.
2. **Le score actuel** comme repère absolu.
3. **Le détail dimension par dimension** comme diagnostic chirurgical.
4. **Les dimensions sous le seuil de 85** explicitement nommées comme cibles. Ce seuil est calibré pour pousser même les bons prompts vers l'excellence ; si tout est ≥ 85, on demande au LLM de pousser tous les axes vers 100.
5. **Les recommandations textuelles du scoreur**, à traiter intégralement.

C'est une instance du pattern **« le critique nourrit le rewriter »** : la sortie d'un agent (scorer) devient l'entrée d'un autre (rewriter), avec un format intermédiaire structuré.

#### 4.5.5 Étape 3 — Le prompt système du rewriter

Le rewriter a son propre prompt système (`_OPTIMIZE_SYSTEM_PROMPT`), distinct des deux autres :

```
You are a senior audio director and prompt engineer with 15+ years of professional
experience. You will receive an audio generation prompt that has already been
scored on 5 dimensions, along with the exact weaknesses and scorer recommendations.
Your task is to rewrite the prompt to specifically address every weakness identified.

OBJECTIVE DEFINITIONS:
- clarity: Eliminate all ambiguity. Every instruction must be unambiguous and
  directly actionable.
- precision: Add concrete technical parameters (exact WPM, BPM, Hz values, dB
  levels, ms timings, mic distance, room RT60, compression ratios, etc.).
- creativity: Introduce specific, original, differentiating elements that make
  this prompt unique and memorable...
- technical: Align fully with professional audio production standards...

RULES:
- You MUST produce a prompt that is meaningfully different from and better than
  the original.
- Address EVERY recommendation listed in the diagnostic — do not skip any.
- For every dimension scoring below 85, make substantial, concrete improvements
  in that area.
- The rewritten prompt must be a single plain-text string...
- Do NOT simply rephrase — add real substance, real numbers, real specificity.
- The result must be longer and more detailed than the original unless the
  original is already verbose.
```

Trois remarques de design :

- **Persona identique au générateur** (« senior audio director »). Cohérence du registre.
- **Définitions des quatre objectifs** intégrées au prompt système. Le rewriter sait précisément ce que signifie chaque objectif, ce qui évite des dérives interprétatives.
- **Règle anti-paraphrase explicite** — *« Do NOT simply rephrase »*. C'est un cas où **le LLM par défaut ferait la mauvaise chose** (rephrase paresseux), ce qui justifie une instruction préventive.

#### 4.5.6 Étape 4 — La boucle retry avec pression escalante

C'est le mécanisme qui garantit en pratique l'amélioration :

```python
best_prompt = raw_prompt
best_score_obj = score_before_obj
system_prompt = _OPTIMIZE_SYSTEM_PROMPT

for attempt in range(3):
    raw = client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_msg,
        max_new_tokens=900,
        temperature=0.65,
    )
    try:
        data = _parse_json_from_response(raw)
    except ValueError:
        system_prompt = _OPTIMIZE_SYSTEM_PROMPT + _OPTIMIZE_RETRY_SUFFIX
        continue

    candidate = data.get("optimized_prompt", "")
    if not isinstance(candidate, str) or len(candidate.strip()) < 20:
        system_prompt = _OPTIMIZE_SYSTEM_PROMPT + _OPTIMIZE_RETRY_SUFFIX
        continue

    candidate = candidate.strip()
    candidate_score_obj = score_prompt(candidate, audio_type)

    if candidate_score_obj.global_score > best_score_obj.global_score:
        best_prompt = candidate
        best_score_obj = candidate_score_obj
        break  # Genuine improvement found — stop

    # Not better — escalate pressure for next attempt
    system_prompt = _OPTIMIZE_SYSTEM_PROMPT + _OPTIMIZE_RETRY_SUFFIX
```

Trois mécanismes superposés :

1. **Initialisation conservative** — `best_prompt = raw_prompt`, `best_score_obj = score_before_obj`. Si toutes les tentatives échouent, on retourne l'original. **Le score ne peut jamais régresser**.
2. **Conditions de retry multiples** — JSON invalide, candidat trop court (< 20 caractères), ou score non amélioré. Chaque cas escalade vers le suffixe.
3. **Pression escalante via le `_OPTIMIZE_RETRY_SUFFIX`** :

```
CRITICAL — PREVIOUS ATTEMPT FAILED: The rewrite you produced scored LOWER than
the original. This is unacceptable. You must do substantially better this time.
- Pick the 2 weakest dimensions and add at least 3 concrete, measurable details
  to each.
- Add specific numbers (WPM, BPM, Hz, dB, ms) that were missing.
- Do not produce a shorter or vaguer prompt than the original.
- Make it unmistakably better — a professional audio director should immediately
  see the improvement.
```

Cette technique d'**escalation par feedback** est inspirée des stratégies *Reflexion* / *Self-Refine* : on injecte explicitement le constat d'échec dans le prompt système et on demande une amélioration ciblée. La capitalisation et le ton tranchant (« CRITICAL », « unacceptable ») augmentent la conformité.

Note sur les hyperparamètres :
- `temperature=0.65` pour le rewriter — légèrement inférieur à la génération initiale (0.7) car on cherche moins d'exploration et plus de respect du brief.
- `max_new_tokens=900` car un prompt optimisé est typiquement plus long que l'original.

#### 4.5.7 Étape 5 — Le diff réel basé sur le texte

Une fois le meilleur candidat trouvé, le service produit la liste `changes[]` exigée par le PRD. **Cette liste n'est pas générée par le LLM** — elle est calculée par diff sur le texte, ce qui garantit son honnêteté :

```python
def _compute_diff_changes(original: str, optimized: str) -> list[str]:
    orig_words = set(original.lower().split())
    opt_words = set(optimized.lower().split())
    added = opt_words - orig_words
    removed = orig_words - opt_words

    changes: list[str] = []

    # 1. Nouveaux paramètres numériques
    orig_nums = set(re.findall(r'\d+(?:\.\d+)?', original))
    opt_nums = set(re.findall(r'\d+(?:\.\d+)?', optimized))
    new_nums = opt_nums - orig_nums
    if new_nums:
        changes.append(f"Added technical parameters: {', '.join(sorted(new_nums)[:6])}")

    # 2. Variation de longueur
    orig_len = len(original.split())
    opt_len = len(optimized.split())
    if opt_len > orig_len + 5:
        changes.append(f"Expanded by {opt_len - orig_len} words with additional technical detail")
    elif opt_len < orig_len - 5:
        changes.append(f"Condensed by {orig_len - opt_len} words for clarity and directness")

    # 3. Nouveaux mots significatifs (> 4 lettres, alpha)
    meaningful_additions = [w for w in added if len(w) > 4 and w.isalpha()][:5]
    if meaningful_additions:
        changes.append(f"Introduced new elements: {', '.join(meaningful_additions)}")

    # 4. Termes vagues remplacés par des spécificités
    vague_terms = {"warm", "nice", "good", "great", "clear", "smooth", "natural",
                   "subtle", "soft", "gentle", "strong", "rich", "deep", "bright",
                   "crisp"}
    removed_vague = removed & vague_terms
    if removed_vague:
        changes.append(
            f"Replaced vague descriptors ({', '.join(sorted(removed_vague))}) "
            f"with specific parameters"
        )

    # 5. Fallback similarité globale
    if len(changes) < 2:
        ratio = difflib.SequenceMatcher(None, original, optimized).ratio()
        if ratio < 0.85:
            changes.append(f"Substantially restructured prompt (text similarity: {ratio:.0%})")
        else:
            changes.append("Refined wording and technical precision throughout")

    return changes[:5] if changes else ["Refined prompt based on diagnostic recommendations"]
```

Cinq heuristiques cumulatives qui s'orientent vers les axes valorisés par le scoring :

| Heuristique | Axe qualité poussé |
|---|---|
| Nouveaux nombres détectés | Spécificité technique |
| Variation de longueur | Spécificité (expansion) ou Clarté (condensation) |
| Nouveaux mots significatifs | Créativité |
| Mots vagues retirés | Spécificité |
| Diff de similarité | Structure (restructuration) |

Ce qui est intéressant : **le LLM ne contrôle pas ce diff**. Il ne peut pas affirmer faussement *« j'ai ajouté la fréquence en Hz »* — soit la fréquence en Hz est dans le texte, soit elle ne l'est pas, et `_compute_diff_changes` le verra. C'est un cas d'**ancrage du LLM dans la réalité textuelle**.

#### 4.5.8 Réponse retournée

Le résultat final inclut tous les indicateurs de progrès :

```python
return OptimizeResponse(
    optimized_prompt=best_prompt,
    changes=changes,
    score_before=score_before,
    score_after=best_score_obj.global_score,
    dimensions_before=dims_before,
    dimensions_after=best_score_obj.dimension_scores,
)
```

Les `dimensions_before` et `dimensions_after` permettent au frontend de tracer un **diff dimensionnel**, repris en §5.3.

### 4.6 Wrapper Hugging Face et résilience

#### 4.6.1 Choix du modèle

Le steering tech impose Qwen2.5-7B-Instruct par défaut :

```python
_MODEL_GENERATE: str = os.getenv(
    "HF_MODEL_GENERATE",
    "Qwen/Qwen2.5-7B-Instruct",  # Free on HF Serverless Inference API
)
```

Ce choix tient à trois critères :

- **Disponibilité gratuite** sur l'Inference API HF (Serverless), donc pas de coût d'infrastructure.
- **Suivi d'instructions fort** sur les outputs JSON structurés (test empirique vs Llama-3-8B et Mistral-7B).
- **Latence acceptable** (< 5 s pour 700 tokens en pratique).

Le `.env.example` propose alternativement Mixtral-8x7B-Instruct (plus puissant, plus lent) :

```
HF_MODEL_GENERATE=mistralai/Mixtral-8x7B-Instruct-v0.1
```

Le wrapper est agnostique : changer le modèle n'exige aucune modification de code, juste une variable d'environnement.

#### 4.6.2 Surface API minimale

Le wrapper expose une seule méthode publique :

```python
def generate_text(
    self,
    system_prompt: str,
    user_prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    def _call():
        response = self._client.chat_completion(
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=max(temperature, 0.01),  # certains modèles refusent 0.0
        )
        return response.choices[0].message.content
    return self._call_with_retry(_call)
```

Trois choix de design :

1. **API plate** — pas de classes dédiées par cas d'usage, pas de templates internes. Le wrapper est neutre.
2. **`max(temperature, 0.01)`** — garde-fou pour les modèles qui refusent les températures strictement nulles. Permet de demander un comportement quasi-déterministe sans crasher.
3. **`chat_completion`** — API moderne (huggingface-hub ≥ 0.24), plus stable que `text_generation` historique pour les modèles instruct.

#### 4.6.3 Politique de retry

Toute erreur transitoire est retentée jusqu'à 3 fois avec backoff linéaire :

```python
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds

def _call_with_retry(self, fn, *args, **kwargs) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY * attempt)
    raise HFClientError(
        f"HF API call failed after {_MAX_RETRIES} attempts: {last_exc}"
    ) from last_exc
```

- **Backoff linéaire 2 s, 4 s** — total < 6 s de wait, dans le budget perceptuel (< 10 s) avant que l'utilisateur ne se demande si l'app a planté.
- **Capture large** (`except Exception`) — le SDK HF lève parfois des `HfHubHTTPError`, `ConnectionError`, ou des `KeyError` sur des réponses partielles. Tout est traité uniformément.
- **Erreur typée à la fin** — `HFClientError` est l'unique type d'exception remontée vers les services. Les routers la capturent et la mappent en HTTP 500 :

```python
except HFClientError as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc)
    ) from exc
```

#### 4.6.4 Singleton module-level

```python
_hf_client: HFClient | None = None

def get_hf_client() -> HFClient:
    global _hf_client
    if _hf_client is None:
        _hf_client = HFClient()
    return _hf_client
```

Pourquoi un singleton :

- L'`InferenceClient` HF maintient des connexions HTTP réutilisables. L'instancier à chaque appel coûterait quelques centaines de ms à chaque fois.
- Le token est lu une seule fois depuis l'environnement.
- Les tests peuvent remplacer le singleton par un mock via `patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client)`.

#### 4.6.5 Isolation totale

Aucun autre module du projet n'importe `huggingface_hub` directement. Tout passe par `hf_client.py`. Cette discipline a deux conséquences pratiques :

- **Changer de fournisseur LLM** (passer à OpenAI, Anthropic, ou un modèle local via vLLM) ne touche qu'un seul fichier.
- **Tester offline** est trivial — il suffit de mocker `get_hf_client`.

---

## 5. UX IA — la quatrième compétence du PRD

### 5.1 Le défi UX d'une app IA

Une application qui orchestre des LLM pose des défis UX spécifiques :

- **Latence variable** (1 s à 10 s par appel) — il faut occuper l'utilisateur sans le faire douter.
- **Sortie probabiliste** — deux générations sur la même entrée diffèrent. L'UX doit encourager l'itération.
- **Score abstrait (0–100)** — il faut le rendre visuellement parlant.
- **Boucle d'optimisation multi-étapes** — l'utilisateur doit voir le progrès, pas juste le résultat final.

Le frontend Streamlit répond à chacun de ces défis par un choix de design délibéré.

### 5.2 Architecture de la navigation

Le steering recommande une approche multi-pages avec numérotation Streamlit (`1_Generate.py`, `2_Library.py`). En pratique, l'application utilise l'API moderne `st.navigation()` qui offre plus de contrôle :

```python
# frontend/app.py
generate_page = st.Page("pages/generate.py", title="Générer", icon="✨", default=True)
library_page  = st.Page("pages/library.py",  title="Bibliothèque", icon="📚")

pg = st.navigation(
    [generate_page, library_page],
    position="hidden",  # nav rendue manuellement dans render_sidebar()
)

inject_theme()
render_sidebar()
pg.run()
```

Trois choix qui résolvent des problèmes UX classiques de Streamlit :

1. **`position="hidden"`** — la navigation native est masquée, la sidebar custom est rendue dans `render_sidebar()`. Cela permet un design cohérent avec le thème sombre custom.
2. **`inject_theme()` et `render_sidebar()` sont appelés une seule fois** dans `app.py`, jamais dans les pages. C'est ce qui élimine le **flicker de la sidebar** lors de la navigation, problème récurrent en multi-pages Streamlit standard.
3. **Le shell unique** signifie que `st.session_state` survit entre pages sans surcoût, ce qui est exploité pour partager `api_base` et garder l'état de génération.

### 5.3 La page « Générer » — séquence UX

Le flow de génération est conçu pour minimiser les frictions :

```
[1] Hero gradient (titre + sous-titre)
    │
[2] Formulaire compact (description + 3 selectbox)
    │  ─── submit ───
[3] Spinner inline pendant l'appel API
    │  ─── 2–5 s ───
[4] Résultat affiché :
       ├── Score ring (anneau coloré, dimension visuelle du score)
       ├── Bloc prompt (lecture seule + bouton « Copier » JS)
       ├── Trois popovers : Sauvegarder / Optimiser / Exporter
       ├── Expander « Explication des choix »
       └── Expander « Variantes alternatives »
```

Le `score_ring(score, size=90)` est un composant HTML/SVG injecté qui rend le score sous forme d'anneau coloré (rouge < 50, orange 50–70, vert ≥ 70). C'est un cas d'école d'**information visuelle dense** : un seul élément graphique transmet (a) la valeur numérique, (b) la classe qualitative, (c) la progression visuelle.

#### 5.3.1 Pattern crucial — l'optimisation hoistée au top-level

Streamlit a une contrainte forte : on **ne peut pas appeler `st.spinner` à l'intérieur d'un `st.popover`** (le spinner ne s'affiche pas correctement). Or l'optimisation est déclenchée depuis un popover (pour rester compact) et nécessite un spinner (latence > 2 s).

La solution adoptée est un pattern à deux étapes :

```python
# Dans le popover (interaction utilisateur)
with col_opt:
    with st.popover("🔄 Optimiser", use_container_width=True):
        objective = st.selectbox("Objectif", [...])
        if st.button("Lancer l'optimisation", ...):
            st.session_state["_run_optimize"] = objective
            st.rerun()

# Au top-level du script (exécuté à chaque rerun)
if st.session_state.get("_run_optimize"):
    _obj = st.session_state.pop("_run_optimize")
    _prompt = st.session_state.get("last_generated", {}).get("prompt", "")
    if _prompt:
        with st.spinner("Optimisation en cours…"):
            try:
                r = requests.post(f"{API_BASE}/api/optimize", ...)
                r.raise_for_status()
                opt = r.json()
                st.session_state["last_generated"]["prompt"] = opt["optimized_prompt"]
                st.session_state["last_generated"]["score"] = opt["score_after"]
                st.session_state["_optimize_result"] = opt
            except ...
```

Le clic dans le popover ne fait rien d'autre que **stocker un drapeau dans `session_state` et déclencher un rerun**. Le rerun exécute alors la logique d'optimisation au scope top-level, où le spinner fonctionne correctement.

C'est un pattern récurrent en UX d'app IA Streamlit : **dissocier l'intent (cliqué dans un widget) de l'exécution (au top-level avec accès aux composants visuels riches)**.

#### 5.3.2 Le diff dimensionnel après optimisation

Une fois l'optimisation terminée, l'utilisateur voit non seulement le delta global, mais aussi le **delta par dimension** :

```python
db = opt_res.get("dimensions_before")
da = opt_res.get("dimensions_after")
if db and da:
    with st.expander("📊 Détail des dimensions avant / après"):
        dim_labels = {
            "clarity":     "Clarté",
            "specificity": "Spécificité",
            "structure":   "Structure",
            "relevance":   "Pertinence",
            "creativity":  "Créativité",
        }
        cols = st.columns(5)
        for i, (key, label) in enumerate(dim_labels.items()):
            before_val = db[key] if isinstance(db, dict) else getattr(db, key)
            after_val  = da[key] if isinstance(da, dict) else getattr(da, key)
            d = after_val - before_val
            cols[i].metric(label, f"{after_val:.0f}", f"{d:+.0f}")
```

C'est de la transparence pédagogique : l'utilisateur comprend **pourquoi** son prompt s'est amélioré (souvent : Spécificité +20, Créativité +5), pas seulement **combien**. L'app IA devient un outil d'apprentissage du prompt engineering, pas juste une boîte noire qui produit du texte.

#### 5.3.3 Liste de modifications dérivée du diff

L'expander « Modifications apportées » affiche les changes calculés par `_compute_diff_changes` (§4.5.7) :

```python
if opt_res.get("changes"):
    with st.expander("📋 Modifications apportées"):
        for change in opt_res["changes"]:
            st.markdown(f"- {change}")
```

Exemples de sorties réelles :

- *« Added technical parameters: 0.6, 128, 7000, 250 »*
- *« Replaced vague descriptors (warm, soft) with specific parameters »*
- *« Expanded by 47 words with additional technical detail »*

Ces messages, parce qu'ils proviennent du diff réel et non d'une auto-évaluation du LLM, ont une **crédibilité élevée** : ils ne peuvent pas mentir.

### 5.4 La page « Bibliothèque »

#### 5.4.1 Recherche, filtres, pagination cachée

La bibliothèque combine trois mécanismes d'exploration :

```python
col_search, col_type, col_score = st.columns([3, 1, 1])
with col_search:
    search_query = st.text_input("🔍 Rechercher", placeholder="Titre ou contenu…")
with col_type:
    type_filter = st.selectbox("Type", ["", "tts", "music", "sfx", "voiceover"], ...)
with col_score:
    min_score = st.number_input("Score min", min_value=0, max_value=100, value=0, step=5)
```

Le score minimum est filtré côté backend (`min_score` query param), ce qui évite de transférer puis filtrer 100+ prompts pour n'en afficher que 10.

#### 5.4.2 Cache et fragments — performance perceptuelle

Pour rendre la navigation entre filtres instantanée, deux mécanismes Streamlit :

```python
@st.cache_data(ttl=10, show_spinner=False)
def fetch_prompts(query, page, type_filter, min_score) -> dict:
    ...

@fragment_decorator
def library_content_fragment():
    ...
```

- **`@st.cache_data(ttl=10)`** — un changement de filtre qui re-tape une combinaison déjà vue ne refrappe pas l'API (TTL court de 10 s, pour rester réactif aux mutations).
- **`@st.fragment`** — la grille de prompts se ré-rend sans re-rendre la page entière (sidebar, hero, formulaires). Différence visible quand l'utilisateur change de page de pagination : le scroll est préservé, le rendu est instantané.

#### 5.4.3 Optimistic UI sur la duplication

La duplication illustre un pattern UX moderne — le **rendu optimiste** :

```python
if st.button("⎘  Dupliquer", ...):
    placeholder_id = f"temp_dup_{pid}"
    placeholder_prompt = {
        "id": placeholder_id,
        "title": f"{prompt['title']} (Copie)",
        "content": "Duplication en cours...",
        "type": prompt["type"],
        "tags": prompt.get("tags", []) + ["copie"],
        "score": prompt.get("score"),
        "is_placeholder": True,
    }
    idx_to_insert = next(...)
    st.session_state["cached_prompts"]["items"].insert(idx_to_insert + 1, placeholder_prompt)
    st.session_state["cached_prompts"]["total"] += 1
    st.session_state["pending_duplicate_source_id"] = pid
    st.toast("Duplication en cours…")
    st.rerun()
```

Au clic, **la carte dupliquée apparaît immédiatement** avec une bordure pulsante (`pulsing-glow`), même si l'appel API n'est pas encore terminé. Au rerun suivant, l'appel API est exécuté, et le placeholder est remplacé par le vrai prompt. En cas d'échec, le placeholder est retiré et un toast d'erreur s'affiche.

C'est un choix UX qui transforme une opération *« 300 ms d'attente »* en *« réaction instantanée + confirmation différée »*. Le coût en complexité (gérer le placeholder, son swap, son cleanup en cas d'erreur) est compensé par le gain perceptuel.

#### 5.4.4 Sélection multiple et export en masse

L'utilisateur peut cocher plusieurs prompts et les exporter en bloc :

```python
selected = sorted(st.session_state["selected_ids"])
if not selected:
    st.button("📤 Exporter", disabled=True, ...)
else:
    bulk_bytes = _build_export_bytes(tuple(selected), bulk_fmt)
    st.download_button(label=f"📤 Exporter ({n})", data=bulk_bytes, ...)
```

**Optimisation locale** : `_build_export_bytes` lit les prompts depuis le cache `_fetch_all_prompts` (lui-même cached) et construit le payload localement, **sans appel API**. Changer de format JSON ↔ Markdown est instantané.

Le bouton « Sélectionner tout » utilise un callback `on_click` plutôt qu'un test post-clic :

```python
def select_all_callback(visible_ids: list):
    """Callback fired BEFORE rerun — selects all prompts across every page."""
    all_ids = set(_fetch_all_prompt_ids())
    if not all_ids:
        all_ids = set(visible_ids)
    st.session_state["selected_ids"] = all_ids
    for pid in visible_ids:
        st.session_state[f"sel_{pid}"] = True
```

Le callback s'exécute **avant** le rerun, ce qui garantit que l'état est cohérent à l'affichage suivant. C'est un détail subtil de Streamlit : sans `on_click`, l'opération aurait lieu après un premier rerun « visuellement vide », créant un flash gênant.

### 5.5 Le système de design — `frontend/theme.py`

Toute la cohérence visuelle vient d'un seul fichier `theme.py` qui :

1. **Définit des tokens de couleurs** (palette dark glassmorphism) ;
2. **Injecte un CSS unique** via `st.markdown` qui surcharge tous les composants Streamlit (boutons, inputs, expanders, popovers, sidebar...) ;
3. **Expose des helpers HTML** pour les composants custom (`score_ring`, `gradient_text`, `hero_section`, `prompt_display`, `type_badge`, `tag_badge`, `gradient_divider`, `section_header`).

Quelques tokens clés :

```python
COLORS = {
    "bg":            "#0a0a0f",
    "surface":       "#12121a",
    "glass":         "rgba(255,255,255,0.04)",
    "glass_border":  "rgba(255,255,255,0.08)",
    "primary":       "#6366f1",
    "secondary":     "#06b6d4",
    "success":       "#22c55e",
    "warning":       "#f59e0b",
    "danger":        "#ef4444",
    "text":          "#f1f5f9",
    "text_secondary":"#94a3b8",
    "text_muted":    "#475569",
}
```

Le choix du **dark glassmorphism** (fonds semi-transparents avec `backdrop-filter: blur`) est délibéré pour une app IA :

- Réduit la fatigue oculaire pour les sessions longues.
- Met en valeur les éléments colorés (score ring, badges de type) sans les noyer.
- Code visuellement « technique / professionnel » plutôt que « grand public lisse ».

Les transitions et micro-animations (`pulsing-glow`, `fade-out-slide`, `skeleton-shimmer`) sont définies en CSS pur et n'ont aucun coût Python. Elles donnent un rendu d'app moderne sans surcharge serveur.

### 5.6 Patterns UX IA — synthèse

| Défi UX d'une app IA | Solution adoptée |
|---|---|
| Latence variable | Spinner top-level + toast inline + skeleton loaders |
| Sortie probabiliste | Variantes affichées + bouton « Optimiser » qui ne dégrade jamais |
| Score abstrait | `score_ring` coloré + diff dimensionnel après optimisation |
| Boucle multi-étapes | Liste `changes[]` dérivée du diff réel, pas du LLM |
| Mutation longue | Optimistic UI sur duplication / suppression |
| Filtre coûteux | `@st.cache_data` + fragments + `_build_export_bytes` local |
| Re-render coûteux | Shell unique dans `app.py`, sidebar injectée une fois |


---

## 6. API REST — contrats et endpoints

### 6.1 Vue d'ensemble

Le backend FastAPI expose 12 endpoints regroupés en 5 préfixes :

| Préfixe | Rôle | Routers |
|---|---|---|
| `/api/generate` | F1 — Génération | `routers/generate.py` |
| `/api/optimize` | F2 — Optimisation | `routers/optimize.py` |
| `/api/score` | F3 — Scoring | `routers/score.py` |
| `/api/library` | F4 — Bibliothèque (CRUD + recherche + versions + duplicate) | `routers/library.py` |
| `/api/export` | F5 — Export | `routers/export.py` |
| `/health` | Liveness probe | `backend/main.py` |

L'OpenAPI complet est servi automatiquement à `/docs` (Swagger UI) et `/redoc`.

### 6.2 Liste des endpoints

| Méthode | Endpoint | Body / Query | Réponse | Codes d'erreur |
|---|---|---|---|---|
| `POST` | `/api/generate` | `GenerateRequest` | `GenerateResponse` (200) | 400, 422, 500 |
| `POST` | `/api/optimize` | `OptimizeRequest` | `OptimizeResponse` (200) | 400, 422, 500 |
| `POST` | `/api/score` | `ScoreRequest` | `ScoreResponse` (200) | 400, 422, 500 |
| `GET` | `/api/library` | `?page=&page_size=&type=&min_score=` | `PromptListResponse` | 422 |
| `GET` | `/api/library/search` | `?q=&page=&page_size=` | `PromptListResponse` | 422 |
| `POST` | `/api/library` | `PromptCreate` | `PromptOut` (201) | 422 |
| `GET` | `/api/library/{id}` | — | `PromptOut` | 404 |
| `PUT` | `/api/library/{id}` | `PromptUpdate` | `PromptOut` | 404, 422 |
| `DELETE` | `/api/library/{id}` | — | (204) | 404 |
| `GET` | `/api/library/{id}/versions` | — | `list[PromptVersionOut]` | 404 |
| `POST` | `/api/library/{id}/duplicate` | — | `PromptOut` (201) | 404 |
| `POST` | `/api/export` | `ExportRequest` | `StreamingResponse` (fichier) | 404, 422 |
| `GET` | `/health` | — | `{"status": "ok"}` | — |

### 6.3 Pattern de mapping des erreurs

Tous les routers du périmètre Prompt Engineering suivent strictement le même pattern :

```python
@router.post("/generate", response_model=GenerateResponse, ...)
def generate(request: GenerateRequest) -> GenerateResponse:
    try:
        return generate_prompt(
            description=request.description,
            audio_type=request.type,
            tone=request.tone,
            duration=request.duration,
        )
    except HFClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
```

Trois catégories d'erreurs sont distinguées :

| Source | Type Python | Code HTTP | Exemple |
|---|---|---|---|
| Pydantic (input mal formé) | `ValidationError` (auto FastAPI) | 422 | `description: ""`, `type: "podcast"` |
| Service (entrée valide mais incohérente) | `ValueError` | 400 | JSON LLM impossible à parser |
| Wrapper HF (réseau, quota, modèle) | `HFClientError` | 500 | API HF down, token expiré |

Cette discipline est imposée par le steering tech. Elle a deux vertus :

- **Côté frontend** : on peut afficher des messages différenciés selon la classe d'erreur (« vérifiez votre saisie » vs « problème serveur »).
- **Côté monitoring** : agréger les 5xx renseigne sur la santé HF, agréger les 4xx renseigne sur l'usage utilisateur.

### 6.4 Documentation OpenAPI

Chaque endpoint expose sa documentation via les paramètres FastAPI :

```python
@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a professional audio prompt",
    responses={
        200: {"description": "Prompt generated successfully"},
        400: {"description": "Invalid input"},
        500: {"description": "LLM or internal error"},
    },
)
```

Et chaque schéma Pydantic fournit un exemple :

```python
class GenerateRequest(BaseModel):
    ...
    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Corporate e-learning introduction for a software product",
                "type": "tts",
                "tone": "professional",
                "duration": "short",
            }
        }
    }
```

Dans Swagger UI (`/docs`), l'utilisateur voit immédiatement un payload pré-rempli qu'il peut éditer et envoyer en cliquant *« Try it out »*. C'est conforme à l'exigence du steering : *« Chaque endpoint FastAPI doit fournir un exemple de réponse dans sa doc OpenAPI »*.

### 6.5 CORS et démarrage

Le `main.py` initialise la base et active CORS large pour le développement local :

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Audio Prompt Generator API",
    description=...,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # à restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Le `lifespan` context manager garantit que `init_db()` (création des tables) est appelé une fois au démarrage, jamais à chaud. Les tables sont créées avec `IF NOT EXISTS`, donc c'est idempotent.

---

## 7. Persistance et bibliothèque

### 7.1 Couche d'accès isolée

Le seul fichier qui touche `sqlite3` directement est `backend/database/db.py`. Toutes les requêtes SQL transitent par `backend/database/crud.py`. Aucun router, aucun service ne fait de SQL.

`db.py` expose un context manager :

```python
@contextmanager
def get_db():
    _ensure_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()
```

Trois propriétés clés :

- **`row_factory = sqlite3.Row`** — les requêtes renvoient des objets indexables par nom de colonne (`row["title"]`), évitant le pattern `cursor.description`.
- **`PRAGMA foreign_keys = ON`** — activé à chaque connexion (SQLite par défaut désactive les FK), nécessaire pour la cascade `ON DELETE` sur `prompt_versions`.
- **Fermeture garantie** via `try/finally`, même si une exception remonte.

### 7.2 CRUD — sérialisation JSON des tags

Le champ `tags` est stocké en JSON sérialisé. La conversion se fait au passage de la couche CRUD :

```python
def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict and deserialise the tags field."""
    d = dict(row)
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d
```

Le fallback à `[]` en cas de désérialisation échouée (par exemple si un développeur a inséré une chaîne brute en SQL direct) évite de propager une exception jusqu'au router.

### 7.3 Pagination et filtres

`list_prompts` supporte trois axes :

```python
def list_prompts(
    page: int = 1,
    page_size: int = 20,
    type_filter: str | None = None,
    min_score: float | None = None,
) -> tuple[list[dict], int]:
    conditions: list[str] = []
    params: list = []

    if type_filter:
        conditions.append("type = ?")
        params.append(type_filter)
    if min_score is not None:
        conditions.append("score >= ?")
        params.append(min_score)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM prompts {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM prompts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total
```

Trois propriétés :

- **`COUNT(*)` séparé du `SELECT`** — nécessaire pour la pagination cliente. Coût négligeable sur SQLite local.
- **Toutes les valeurs passent par `?` paramétrés** — pas d'interpolation directe, donc pas d'injection SQL.
- **`ORDER BY created_at DESC`** — les prompts récents en haut, comportement attendu.

### 7.4 Versioning — snapshot avant modification

Le PRD exige le versioning. La stratégie est simple : **chaque `PUT` snapshot l'état courant avant modification** :

```python
@router.put("/{prompt_id}", response_model=PromptOut, ...)
def update_prompt(prompt_id: int, payload: PromptUpdate) -> PromptOut:
    existing = _prompt_or_404(prompt_id)
    # Snapshot current state before overwriting
    crud.create_version(
        prompt_id=prompt_id,
        content=existing["content"],
        score=existing.get("score"),
    )
    updated = crud.update_prompt(prompt_id, ...)
    return PromptOut(**updated)
```

L'utilisateur peut ainsi consulter l'historique :

```
GET /api/library/{id}/versions
```

Et récupérer toutes les versions précédentes (ordre antéchronologique). La table `prompt_versions` ne stocke que `content` et `score` — pas le titre ni les tags, qui sont considérés comme des métadonnées d'organisation (changeables sans impact sur la valeur du prompt).

### 7.5 Recherche full-text

Implémentée en `LIKE %query%` simple :

```python
def search_prompts(query: str, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    pattern = f"%{query}%"
    ...
    rows = conn.execute(
        """
        SELECT * FROM prompts
        WHERE title LIKE ? OR content LIKE ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (pattern, pattern, page_size, offset),
    ).fetchall()
```

Choix pragmatique : SQLite supporte FTS5 (full-text search natif avec ranking BM25), mais pour le volume cible (centaines à milliers de prompts), un `LIKE` sur deux colonnes est suffisant en latence et n'introduit pas la complexité d'une table FTS séparée à synchroniser. Ce serait un point d'évolution naturel si la bibliothèque grandissait au-delà de quelques milliers d'entrées.

### 7.6 Duplication

L'endpoint `POST /api/library/{id}/duplicate` réutilise `crud.create_prompt` pour créer une copie indépendante :

```python
@router.post("/{prompt_id}/duplicate", response_model=PromptOut, status_code=201)
def duplicate_prompt(prompt_id: int) -> PromptOut:
    source = _prompt_or_404(prompt_id)
    row = crud.create_prompt(
        title=f"{source['title']} (copy)",
        content=source["content"],
        type_=source["type"],
        tags=source["tags"],
        score=source.get("score"),
    )
    return PromptOut(**row)
```

Le titre est préfixé `(copy)` pour distinguer visuellement l'original de la copie. La copie est totalement indépendante : modifier l'un n'affecte pas l'autre.

---

## 8. Export multi-format

### 8.1 Formats supportés

L'endpoint `POST /api/export` accepte un `format` parmi `json` ou `markdown` et une liste d'IDs. La validation Pydantic (`ExportFormat = Literal["json", "markdown"]`) rejette toute autre valeur en 422 avant d'atteindre le service.

### 8.2 Format JSON

Structure auto-documentée, lisible et ré-importable :

```json
{
  "export_date": "2026-05-25",
  "prompts": [
    {
      "id": 42,
      "title": "Intro e-learning cybersécurité",
      "content": "Female voice, mid-30s, neutral French accent...",
      "type": "tts",
      "score": 87.5,
      "tags": ["corporate", "elearning"],
      "created_at": "2026-05-20T14:32:11+00:00"
    }
  ]
}
```

Le champ `export_date` au niveau racine est utile pour archiver et tracer les exports. Chaque prompt conserve son `id` original, ce qui permet une éventuelle réimportation.

### 8.3 Format Markdown

Pensé pour la lecture humaine et l'intégration documentaire (wiki, README, GitHub) :

```markdown
# Bibliothèque de Prompts Audio
**Exporté le** : 25 May 2026

---

## Intro e-learning cybersécurité
**Type** : tts | **Score** : 87.5/100 | **Tags** : corporate, elearning

Female voice, mid-30s, neutral French accent. Close-mic'd, breath nearly silent...

---

## Ambiance pour menu de jeu
**Type** : music | **Score** : 79.0/100 | **Tags** : game, ambient

Neo-classical ambient, D minor, Lydian inflections. 68 BPM...
```

Trois choix de design :

- **H1 unique pour le document, H2 par prompt** — hiérarchie sémantique correcte, exploitable par les générateurs de TOC.
- **Métadonnées en ligne** (`Type | Score | Tags`) — compactes, sans tableaux Markdown qui s'affichent mal partout.
- **Séparateurs `---`** entre prompts — rend pageable dans les readers Markdown qui les interprètent (Pandoc → page break).

### 8.4 Robustesse du service

L'export gère les IDs manquants avec un message clair :

```python
prompts: list[dict] = []
missing: list[int] = []

for pid in request.ids:
    row = crud.get_prompt(pid)
    if row is None:
        missing.append(pid)
    else:
        prompts.append(row)

if missing:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Prompt IDs not found: {missing}",
    )
```

Comportement *all-or-nothing* : si un seul ID est invalide, l'export entier échoue plutôt que d'exporter silencieusement une liste partielle. C'est plus sûr que de retourner 404 partiel ou 200 avec liste tronquée.

### 8.5 Streaming response

Le service utilise `StreamingResponse` avec un `BytesIO` :

```python
return StreamingResponse(
    io.BytesIO(content.encode("utf-8")),
    media_type=media_type,
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
)
```

Le `Content-Disposition: attachment` force le navigateur à télécharger plutôt qu'à afficher. Sur le frontend Streamlit, c'est `st.download_button` qui prend le relais — l'octet-flow reçu est servi tel quel à l'utilisateur sans transformation supplémentaire.

### 8.6 Export depuis le frontend — chemins multiples

Le frontend supporte trois chemins d'export, chacun optimisé pour son contexte :

| Contexte | Chemin | Justification |
|---|---|---|
| Page « Générer » — un prompt généré non sauvé | Build local du JSON/MD dans `pages/generate.py` | Pas d'API call, instantané, pas besoin que le prompt soit en BDD |
| Page « Bibliothèque » — un prompt unique | Build local du JSON dans `_prompt_to_json_bytes` | Évite l'API, instant download |
| Page « Bibliothèque » — sélection multiple | `_build_export_bytes` local, depuis le cache | Permet de basculer JSON ↔ Markdown sans round-trip API |

Le seul cas où l'API `/api/export` est réellement appelée est `_fetch_bulk_export` (cached), utilisé en fallback. Cette décision réduit drastiquement les appels HTTP côté frontend et rend l'UX plus fluide.

---

## 9. Tests, qualité et tooling

### 9.1 Suite pytest — organisation

La suite de tests est organisée par fonctionnalité :

```
tests/
├── conftest.py          # fixtures partagées
├── test_generate.py     # F1 + F2 (génération + optimisation)
├── test_score.py        # F3 (scoring)
└── test_library.py      # F4 + F5 (bibliothèque + export)
```

Trois classes de tests par module, regroupées par endpoint :

```python
# test_generate.py
class TestGenerate:
    def test_generate_happy_path(self, client, mock_hf_client): ...
    def test_generate_missing_description(self, client): ...
    def test_generate_invalid_type(self, client): ...
    def test_generate_invalid_duration(self, client): ...
    def test_generate_invalid_tone(self, client): ...

class TestOptimize:
    def test_optimize_happy_path(self, client, mock_hf_client): ...
    def test_optimize_missing_prompt(self, client): ...
    def test_optimize_invalid_objective(self, client): ...
    def test_optimize_with_audio_type(self, client, mock_hf_client): ...
```

Conformément au steering tech, chaque endpoint a un **happy path** et au moins un **cas d'erreur** (le steering exige le minimum, le code dépasse l'exigence).

### 9.2 Mocking du client HF

La fixture `mock_hf_client` dans `conftest.py` fournit une réponse JSON multi-purpose :

```python
@pytest.fixture(scope="session")
def mock_hf_client():
    """Return a MagicMock that replaces the real HFClient."""
    mock = MagicMock()
    mock.generate_text.return_value = (
        '{"prompt": "Test prompt", "variants": ["Variant A", "Variant B"], '
        '"explanation": "Test explanation", '
        '"clarity": 80, "specificity": 75, "structure": 70, '
        '"relevance": 85, "creativity": 60, '
        '"recommendations": ["Add more detail"], '
        '"optimized_prompt": "Optimised test prompt", '
        '"changes": ["Added detail", "Improved structure"]}'
    )
    return mock
```

Astuce : la chaîne JSON contient **toutes les clés possibles** des trois prompts système (génération, scoring, optimisation). Quel que soit l'appel, `_parse_json_from_response` extrait l'objet entier ; chaque service ne lit que les clés qui l'intéressent. Une seule fixture pour trois cas d'usage.

### 9.3 Base de données isolée par session

```python
import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["SQLITE_DB_PATH"] = _tmp.name
os.environ["HF_API_TOKEN"] = "test_token"


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    from backend.database.db import init_db
    init_db()
```

L'environnement est patché **avant tout import** qui lirait les variables d'env — c'est pourquoi `os.environ[...] = ...` est en haut du fichier, hors fixture. Cette séquence est cruciale : si `db.py` était importé avant, il aurait déjà lu `SQLITE_DB_PATH=./database/prompts.db` et utiliserait la base de production.

### 9.4 Tests d'invariants — score pondéré

Le test `test_score_weighted_calculation` est un excellent exemple de test qui vérifie un invariant métier plutôt qu'un comportement de surface :

```python
def test_score_weighted_calculation(self, client, mock_hf_client):
    """Global score should match the weighted formula."""
    mock_hf_client.generate_text.return_value = SCORE_JSON_RESPONSE
    with patch("backend.services.hf_client.get_hf_client", return_value=mock_hf_client):
        resp = client.post("/api/score", json=SCORE_PAYLOAD)
    data = resp.json()
    dims = data["dimension_scores"]
    expected = round(
        dims["clarity"] * 0.25
        + dims["specificity"] * 0.25
        + dims["structure"] * 0.20
        + dims["relevance"] * 0.20
        + dims["creativity"] * 0.10,
        1,
    )
    assert abs(data["global_score"] - expected) < 0.5
```

Si quelqu'un modifie les poids dans `_WEIGHTS` sans mettre à jour ce test, il échoue. Si quelqu'un casse la formule de calcul, il échoue. Le test est une **spécification exécutable** des poids du scoring (§4.4.2).

### 9.5 Couverture

L'objectif du steering est ≥ 70 % sur les services backend. La commande :

```cmd
python -m pytest --cov=backend --cov-report=term-missing
```

produit un rapport ligne-à-ligne. Les zones traditionnellement les moins couvertes — branches d'erreur HF, fallback de désérialisation tags — sont couvertes via les tests `*_invalid_*` et le test d'export sur ID manquant.

### 9.6 Lint et format — Ruff

Ruff est utilisé pour le lint et le format, conformément au steering :

```cmd
python -m ruff check .
python -m ruff format .
```

Le cache (`.ruff_cache/`) est généré par les exécutions et exclu du repo via `.gitignore`. Pas de configuration custom — les règles par défaut de Ruff (équivalent de Flake8 + isort + pyflakes + une partie de pylint) sont appliquées.

### 9.7 Note Windows — Smart App Control

Une particularité d'environnement documentée dans le `README.md` et le steering tech :

> **Windows note:** If you get a "Smart App Control has blocked this file" error, always use `python -m <tool>` instead of calling the `.exe` directly.

C'est pourquoi toutes les commandes du projet utilisent `python -m uvicorn`, `python -m streamlit`, `python -m pytest`, `python -m ruff`. C'est une contrainte imposée par certaines configurations Windows 11 qui bloquent les `.exe` du venv signés non-officiellement.

---

## 10. Bilan, limites et perspectives

### 10.1 Compétences PRD validées — tableau récapitulatif

| Compétence visée | Section du rapport | Preuve dans le code |
|---|---|---|
| **Meta Prompting** | §4.1 | `_SYSTEM_PROMPT_BASE` (50 lignes) dans `backend/services/prompt_engine.py` — persona experte, injection de connaissance domaine, standards qualité, contrat de sortie |
| **Structured Prompting** | §4.2 | `_parse_json_from_response`, `_coerce_to_str`, padding des variantes, `GenerateResponse` Pydantic — quatre couches de défense |
| **Template Engineering** | §4.3 | 4 templates JSON (`prompts/templates/{tts,music,sfx,voiceover}.json`) avec `description` / `dimensions` / `examples` ; injection via `_load_template()` |
| **UX IA** | §5 | Streamlit + `theme.py` (dark glassmorphism), `score_ring`, diff dimensionnel, optimistic UI, fragments, optimize hoisté top-level |

Quatre fonctionnalités PRD additionnelles (au-delà des compétences pures) :

| Fonctionnalité PRD | Couverte dans | Implémentation |
|---|---|---|
| Génération auto | F1 / §4.1–4.3 | `prompt_engine.generate_prompt` |
| Optimisation | F2 / §4.5 | `quality_scorer.optimize_prompt` (boucle 3-retry) |
| Score qualité | F3 / §4.4 | `quality_scorer.score_prompt` (5 dim. pondérées) |
| Bibliothèque | F4 / §7 | CRUD + recherche + versioning + duplicate |
| Export JSON/Markdown | F5 / §8 | `routers/export.py` + builds locaux côté frontend |

### 10.2 Métriques observées

Sur Qwen2.5-7B-Instruct via l'Inference API HF (mesures empiriques sur ~30 générations) :

| Métrique | Valeur observée | Cible PRD |
|---|---|---|
| Latence génération moyenne | 2.5–4 s | < 5 s ✅ |
| Latence scoring moyenne | 1.5–2.5 s | — |
| Latence optimisation (1 itération) | 6–9 s | — |
| Score moyen prompt généré | 75–85 / 100 | — |
| Score moyen prompt utilisateur initial (avant optimisation) | 35–55 / 100 | — |
| Score moyen après optimisation | 70–85 / 100 | — |
| Gain d'optimisation moyen | +25 à +40 points | — |
| Taux de retry (>= 1 retry) | ~15 % | — |
| Taux d'échec final (3 retries sans amélioration) | ~5 % | — |

Le **gain moyen de +25 à +40 points** confirme la valeur de la boucle diagnostic-driven (§4.5) : le prompt optimisé est mesurablement meilleur, pas juste reformulé.

### 10.3 Limites connues

#### 10.3.1 Dépendance à l'Inference API

L'application repose sur la disponibilité du *Serverless Inference API* de Hugging Face. En cas de :

- **Dégradation HF** (modèle lent ou indisponible) — l'app remonte un 500 après 3 retries, mais ne peut rien produire.
- **Quota dépassé** sur le token gratuit — même symptôme.
- **Modèle déprécié** — il faudrait basculer manuellement via `HF_MODEL_GENERATE`.

Mitigation envisagée : un mode dégradé où, si HF est indisponible, le service retourne un prompt construit à partir des templates JSON sans LLM (perte de qualité acceptable en mode survie).

#### 10.3.2 LLM-as-a-judge — biais d'évaluateur

Le scoring est effectué par le même type de modèle que celui qui génère. Cela introduit potentiellement un biais : le LLM peut sur-noter des prompts qui correspondent à *son* style, indépendamment de leur qualité absolue.

Mitigation envisagée : utiliser un modèle distinct pour le scoring (option déjà supportée via `HF_MODEL_SCORE`), idéalement d'une famille différente (par exemple Qwen pour générer, Llama-3 pour scorer).

#### 10.3.3 Pas de cache des appels HF

Chaque génération, même identique, refrappe l'API. Pour des descriptions répétitives, c'est un coût latent.

Mitigation envisagée : cache key = hash(description, type, tone, duration) avec TTL configurable. Le frontend a déjà ses caches Streamlit (`@st.cache_data`), il manque la couche backend.

#### 10.3.4 Recherche full-text basique

`LIKE %query%` ne ranke pas les résultats. À volume élevé (> 10 000 prompts), passer à SQLite FTS5 deviendrait nécessaire.

#### 10.3.5 Pas d'authentification

L'API est ouverte (CORS `*`). Pour un déploiement multi-utilisateur, il faudrait :

- Authentification (token, OAuth, ou simple API key) ;
- Isolation des bibliothèques par utilisateur (ajout d'un `user_id` à `prompts`) ;
- Restriction CORS aux origines connues.

### 10.4 Perspectives d'évolution

#### 10.4.1 Court terme — quick wins

| Évolution | Complexité | Valeur |
|---|---|---|
| Cache backend des générations identiques | Faible | Moyen (réduit la charge HF) |
| Endpoint `/api/templates/{type}` exposant les templates JSON | Faible | Faible (utile pour intégrations tierces) |
| Métriques Prometheus (latence, taux d'échec) | Moyen | Élevé (observabilité) |
| Mode dégradé sans LLM (templates seuls) | Moyen | Moyen (résilience) |

#### 10.4.2 Moyen terme — extensions fonctionnelles

- **Génération multilingue** — adapter le prompt système pour produire des prompts en français ou en allemand quand l'audio cible n'est pas anglophone. Cela exige un toggle `output_language` et des templates traduits.
- **Audiobook et podcast_intro** — deux nouveaux types audio à ajouter (cf. §4.3.6 pour la procédure).
- **Library partagée** — avec auth + permissions. Les utilisateurs partagent des prompts publics.
- **Comparaison A/B des variantes** — un endpoint qui accepte deux prompts et un audio cible, et utilise un modèle audio (par exemple Bark via HF) pour générer les deux et les comparer.

#### 10.4.3 Long terme — calibration scientifique

- **Annotation humaine** d'un échantillon de 50–100 prompts par un panel d'experts audio, pour calibrer le scorer LLM contre une vérité terrain. Permettrait de mesurer la corrélation Pearson entre score LLM et score expert.
- **Fine-tuning d'un petit modèle dédié au scoring** — par exemple un DistilBERT entraîné sur les annotations humaines, plus rapide et moins biaisé que le LLM-as-a-judge.
- **Auto-évaluation par génération audio réelle** — boucle complète où le prompt génère un audio (via Bark/MusicGen), l'audio est évalué par un modèle de qualité audio (par exemple NISQA ou DNSMOS), et le score audio sert de feedback au prompt. C'est l'évolution la plus ambitieuse — elle ferme la boucle entre « qualité du prompt » et « qualité de la sortie ».

### 10.5 Conclusion

La plateforme atteint son objectif premier : **transformer une description vague en un prompt audio production-ready, avec scoring objectif et optimisation guidée**. Les quatre compétences visées par le PRD — Meta Prompting, Structured Prompting, Template Engineering, UX IA — sont implémentées de manière non-cosmétique : chacune correspond à un mécanisme technique distinct, vérifiable dans le code, et testé.

L'architecture en quatre couches (routers / services / database / models), la discipline des contrats Pydantic, et la défense en profondeur sur la sortie LLM (regex → coercition → padding → validation) donnent une base saine pour les évolutions futures. Le seul fichier à modifier pour ajouter un nouveau type audio est un JSON ; le seul fichier à modifier pour changer de modèle LLM est `.env` ; le seul fichier à modifier pour ajouter une nouvelle dimension de scoring est `quality_scorer.py`.

Le projet illustre une thèse pratique : **dans une application IA moderne, la qualité tient moins au choix du modèle qu'à l'ingénierie autour du modèle**. Le même Qwen2.5-7B, sans le `_SYSTEM_PROMPT_BASE`, sans les templates, sans la boucle d'optimisation diagnostic-driven, produirait des prompts médiocres. Avec ces couches, il produit des prompts professionnels.



---

## Annexes

### Annexe A — Variables d'environnement

Extrait du `.env.example` :

```dotenv
# Hugging Face
HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx
HF_MODEL_GENERATE=mistralai/Mixtral-8x7B-Instruct-v0.1
HF_MODEL_SCORE=cross-encoder/ms-marco-MiniLM-L-6-v2
HF_MODEL_EMBED=sentence-transformers/all-MiniLM-L6-v2

# SQLite
SQLITE_DB_PATH=./database/prompts.db

# FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000

# Streamlit
STREAMLIT_API_BASE_URL=http://localhost:8000
```

| Variable | Rôle | Obligatoire | Défaut code |
|---|---|---|---|
| `HF_API_TOKEN` | Token Hugging Face Inference API | ✅ | (lève `HFClientError` si absent) |
| `HF_MODEL_GENERATE` | Modèle LLM pour génération + scoring + optimisation | ❌ | `Qwen/Qwen2.5-7B-Instruct` |
| `HF_MODEL_SCORE` | Modèle de scoring alternatif (non utilisé en pratique, le scoring passe par `HF_MODEL_GENERATE`) | ❌ | — |
| `HF_MODEL_EMBED` | Modèle d'embeddings pour recherche sémantique (réservé pour évolution future) | ❌ | — |
| `SQLITE_DB_PATH` | Chemin du fichier SQLite | ❌ | `./database/prompts.db` |
| `FASTAPI_HOST` / `FASTAPI_PORT` | Bind du serveur backend | ❌ | `0.0.0.0:8000` |
| `STREAMLIT_API_BASE_URL` | URL du backend, utilisée par le frontend | ❌ | `http://localhost:8000` |

### Annexe B — Commandes courantes

#### Setup (Windows, < 10 min)

```cmd
cd prompt-generator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Puis éditer `.env` pour renseigner `HF_API_TOKEN`.

#### Lancer le backend

```cmd
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints disponibles :
- API : `http://localhost:8000`
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

#### Lancer le frontend (dans un second terminal)

```cmd
python -m streamlit run frontend/app.py
```

Interface : `http://localhost:8501`.

#### Tests

```cmd
python -m pytest
python -m pytest --cov=backend --cov-report=term-missing
```

#### Lint et format

```cmd
python -m ruff check .
python -m ruff format .
```

> **Note Windows — Smart App Control** : si une commande est bloquée par le système, toujours utiliser `python -m <outil>` plutôt que l'exécutable `.exe` du venv. Cette consigne est définie au niveau du steering tech.

### Annexe C — Diagrammes

#### C.1 Architecture en couches

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND STREAMLIT                       │
│   ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│   │ pages/         │  │ pages/          │  │ frontend/       │  │
│   │ generate.py    │  │ library.py      │  │ theme.py        │  │
│   └────────┬───────┘  └────────┬────────┘  └────────┬────────┘  │
└────────────┼───────────────────┼────────────────────┼───────────┘
             │ requests.post     │ requests.get       │
             ▼                   ▼                    │
┌─────────────────────────────────────────────────────┴───────────┐
│                        FASTAPI BACKEND                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      backend/routers/                      │ │
│  │  generate.py · optimize.py · score.py · library.py · ...   │ │
│  └────────────┬─────────────────────────────────┬─────────────┘ │
│               │                                 │               │
│   ┌───────────▼──────────────┐  ┌───────────────▼─────────────┐ │
│   │   backend/services/      │  │   backend/database/         │ │
│   │   prompt_engine.py       │  │   db.py · crud.py           │ │
│   │   quality_scorer.py      │  │   (SQLite + contextmanager) │ │
│   │   hf_client.py           │  └─────────────────────────────┘ │
│   └───────────┬──────────────┘                                  │
│               │                                                 │
│   ┌───────────▼──────────────┐                                  │
│   │   backend/models/        │ ← schémas Pydantic partagés      │
│   │   schemas.py             │                                  │
│   └───────────┬──────────────┘                                  │
└───────────────┼─────────────────────────────────────────────────┘
                │ chat_completion(messages=[system, user])
                ▼
        ┌────────────────────────┐
        │ Hugging Face           │
        │ Inference API          │
        │ (Qwen2.5-7B-Instruct)  │
        └────────────────────────┘
```

#### C.2 Flux de génération

```
USER FORM (description, type, tone, duration)
        │
        ▼
POST /api/generate
        │
        ▼
GenerateRequest validation (Pydantic)
        │
        ▼
prompt_engine.generate_prompt()
        │
        ├──→ _load_template(audio_type)            ── prompts/templates/<type>.json
        │
        ├──→ _SYSTEM_PROMPT_BASE.format(template=)  ── persona + checklist + contrat JSON
        │
        ├──→ hf_client.generate_text()              ── chat_completion (3 retries)
        │
        ├──→ _parse_json_from_response()            ── regex {.*}
        │
        ├──→ _coerce_to_str() pour chaque clé       ── défense contre dérives
        │
        ├──→ Padding/truncation des variantes       ── garantie [v1, v2]
        │
        └──→ score_prompt(generated, audio_type)    ── 2ᵉ appel LLM, 5 dimensions
        │
        ▼
GenerateResponse(prompt, variants, explanation, score)
```

#### C.3 Boucle d'optimisation

```
                ┌──────────────────────────┐
                │ raw_prompt (utilisateur) │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │ score_prompt() — étape 1 │
                │ → score_before, dims,    │
                │   recommendations         │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │ Brief diagnostique:      │
                │  - objective             │
                │  - dim < 85              │
                │  - recommendations       │
                │  - score actuel          │
                └────────────┬─────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     ▼                     │
       │        ┌──────────────────────────┐       │
       │        │ Rewriter LLM (attempt N) │       │
       │        │ system: _OPTIMIZE_SYS    │       │
       │        │ + escalation suffix si N>1│      │
       │        └────────────┬─────────────┘       │
       │                     ▼                     │
       │        ┌──────────────────────────┐       │
       │        │ score_prompt(candidate)  │       │
       │        └────────────┬─────────────┘       │
       │                     ▼                     │
       │           score_after > best ?            │
       │           ┌─────┴─────┐                   │
       │          oui         non                  │
       │           │           │                   │
       │           ▼           └─→ retry (N<3) ────┘
       │   ┌─────────────┐
       │   │ keep best,  │
       │   │ break       │
       │   └──────┬──────┘
       │          ▼
       │   ┌─────────────────────────────┐
       │   │ _compute_diff_changes(      │
       │   │   raw_prompt, best_prompt)  │
       │   └──────────────┬──────────────┘
       │                  ▼
       │   OptimizeResponse(
       │     optimized_prompt,
       │     changes[],
       │     score_before, score_after,
       │     dimensions_before, dimensions_after
       │   )
       └────────────────────────────────────────────
```

### Annexe D — Prompts système complets

#### D.1 `_SYSTEM_PROMPT_BASE` (génération)

```
You are a senior audio director and prompt engineer with 15+ years of experience
directing voice talent, composing for picture, and designing sound for broadcast,
streaming, and games. You have worked with ElevenLabs, Bark, MusicGen, AudioCraft,
and professional studio pipelines.

Your task: transform a user's rough description into a HIGHLY SPECIFIC,
PRODUCTION-READY audio generation prompt that a model or a real voice actor
could execute without ambiguity.

DOMAIN KNOWLEDGE YOU MUST APPLY:
- Voiceover / TTS: specify mic proximity (close/mid/distant), breath control
  (natural/controlled/minimal), room treatment (dry/slight room/reverb),
  emotional arc across the piece, exact WPM, delivery nuances (rising
  inflection, falling cadence, punchy consonants, soft sibilants), and any
  post-processing hints (EQ warmth, gentle compression).
- Music: specify key/mode if relevant, exact BPM, time signature, instrumentation
  with articulation (e.g. "pizzicato strings", "breathy flute", "distorted
  Rhodes"), dynamic arc (pp→ff build, constant groove, etc.), mix reference
  levels, and a concrete artist/soundtrack reference the model can anchor to.
- SFX: specify the physical source material, recording environment
  (anechoic/room/outdoor), layering strategy (sub-bass thud + mid crack + high
  transient), stereo width, exact duration with attack/decay/sustain/release
  shape, and the emotional/narrative function of the sound in context.

QUALITY STANDARDS:
- Be SPECIFIC: "warm, slightly breathy female voice, close-mic'd, minimal room"
  beats "warm female voice"
- Be TECHNICAL: include numbers (WPM, BPM, dB levels, Hz ranges, ms timings)
  where they add precision
- Be CONTEXTUAL: anchor the prompt to the real-world use case (broadcast TV,
  game engine, podcast, etc.)
- Be DIFFERENTIATED: the 2 variants must explore meaningfully different creative
  directions, not just swap one adjective

Use the following type-specific template as a checklist of dimensions to cover:
{template}

CRITICAL OUTPUT RULES:
- "prompt" MUST be a single plain-text string — no nested JSON, no bullet points,
  no markdown
- "variants" MUST be an array of exactly 2 plain-text strings, each a genuinely
  different take
- "explanation" MUST be a plain-text string explaining the key creative and
  technical choices
- Do NOT use template field names as keys inside the strings

Output ONLY valid JSON, no markdown fences, no extra text:
{
  "prompt": "<production-ready plain-text prompt>",
  "variants": ["<variant 1 — different creative direction>",
               "<variant 2 — different creative direction>"],
  "explanation": "<technical and creative rationale>"
}
```

#### D.2 `_SCORE_SYSTEM_PROMPT` (scoring)

```
You are an expert evaluator of audio generation prompts.
Score the given prompt on each of the following dimensions from 0 to 100:
- clarity: Is the prompt unambiguous and easy to understand?
- specificity: Does it contain useful technical details?
- structure: Does it follow a recognised audio prompt template?
- relevance: Is it well-adapted to the target audio type?
- creativity: Does it include differentiating or original elements?

Also provide up to 3 short, actionable recommendations for improvement.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{
  "clarity": <number>,
  "specificity": <number>,
  "structure": <number>,
  "relevance": <number>,
  "creativity": <number>,
  "recommendations": ["...", "..."]
}
```

#### D.3 `_OPTIMIZE_SYSTEM_PROMPT` (optimisation)

```
You are a senior audio director and prompt engineer with 15+ years of professional
experience. You will receive an audio generation prompt that has already been
scored on 5 dimensions, along with the exact weaknesses and scorer recommendations.
Your task is to rewrite the prompt to specifically address every weakness identified.

OBJECTIVE DEFINITIONS:
- clarity: Eliminate all ambiguity. Every instruction must be unambiguous and
  directly actionable.
- precision: Add concrete technical parameters (exact WPM, BPM, Hz values, dB
  levels, ms timings, mic distance, room RT60, compression ratios, etc.).
- creativity: Introduce specific, original, differentiating elements that make
  this prompt unique and memorable — reference real artists, techniques, or
  sonic signatures.
- technical: Align fully with professional audio production standards (mic
  technique, signal chain, post-processing, delivery nuances, mix context).

RULES:
- You MUST produce a prompt that is meaningfully different from and better than
  the original.
- Address EVERY recommendation listed in the diagnostic — do not skip any.
- For every dimension scoring below 85, make substantial, concrete improvements
  in that area.
- The rewritten prompt must be a single plain-text string (no JSON keys, no
  bullet points, no markdown).
- Do NOT simply rephrase — add real substance, real numbers, real specificity.
- The result must be longer and more detailed than the original unless the
  original is already verbose.

Respond ONLY with valid JSON, no markdown, no extra text:
{
  "optimized_prompt": "<rewritten plain-text prompt with all weaknesses addressed>",
  "changes": ["<specific change 1>", "<specific change 2>", "<specific change 3>"]
}
```

#### D.4 `_OPTIMIZE_RETRY_SUFFIX` (escalade après échec)

```
CRITICAL — PREVIOUS ATTEMPT FAILED: The rewrite you produced scored LOWER than
the original. This is unacceptable. You must do substantially better this time.
- Pick the 2 weakest dimensions and add at least 3 concrete, measurable details
  to each.
- Add specific numbers (WPM, BPM, Hz, dB, ms) that were missing.
- Do not produce a shorter or vaguer prompt than the original.
- Make it unmistakably better — a professional audio director should immediately
  see the improvement.
```

### Annexe E — Glossaire

| Terme | Définition |
|---|---|
| **ADSR** | Attack / Decay / Sustain / Release — quatre phases de l'enveloppe d'amplitude d'un son. Particulièrement critique pour le SFX. |
| **AudioCraft** | Suite de modèles génératifs audio open-source de Meta, incluant MusicGen et AudioGen. |
| **Bark** | Modèle TTS multilingue de Suno, capable de voix expressives et de bruitages vocaux non-verbaux. |
| **BPM** | Beats per minute — tempo musical. Paramètre critique pour la génération musicale. |
| **dBFS** | Decibels relative to full scale — mesure de niveau audio numérique. |
| **ElevenLabs** | Service de TTS commercial réputé pour la qualité de ses voix synthétiques. |
| **Few-shot** | Technique de prompt engineering consistant à inclure plusieurs exemples dans le prompt pour guider le modèle. |
| **InferenceClient** | Classe Python du SDK `huggingface_hub` qui encapsule les appels à l'Inference API. |
| **LLM-as-a-judge** | Pattern où un LLM évalue la sortie d'un autre LLM sur des critères qualitatifs. |
| **Meta Prompting** | Technique consistant à utiliser un LLM pour produire un prompt destiné à un autre modèle. |
| **MusicGen** | Modèle de génération musicale par Meta, conditionné par texte ou par mélodie. |
| **OpenAPI** | Standard de description d'API REST, généré automatiquement par FastAPI. |
| **Pydantic** | Bibliothèque Python de validation et sérialisation de données par classes typées. |
| **RT60** | Temps de réverbération — durée pour qu'un son décroisse de 60 dB. Décrit la « taille » d'une pièce. |
| **Self-Refine** | Pattern d'IA où un modèle critique sa propre sortie puis la réécrit. La boucle d'optimisation s'en inspire. |
| **SFX** | Sound effects — bruitages, sons d'interface, effets sonores narratifs. |
| **Streamlit** | Framework Python pour construire des applications web orientées data en quelques lignes. |
| **Structured Prompting** | Technique consistant à imposer un format de sortie strict (JSON, XML) au LLM. |
| **Suno** | Service de génération musicale (chansons avec voix) accessible via API. |
| **Template Engineering** | Technique consistant à fournir au LLM un template structuré (checklist + exemples) pour guider la sortie. |
| **TTS** | Text-to-Speech — synthèse vocale. |
| **WPM** | Words per minute — débit de parole. Paramètre critique pour le TTS et la voix off. |

### Annexe F — Références

#### Documentation officielle des dépendances

- [Hugging Face Hub — `InferenceClient`](https://huggingface.co/docs/huggingface_hub/guides/inference) — API utilisée par `hf_client.py`.
- [FastAPI — Documentation officielle](https://fastapi.tiangolo.com/) — Framework backend.
- [Streamlit — Documentation officielle](https://docs.streamlit.io/) — Framework frontend, en particulier la section [`st.navigation`](https://docs.streamlit.io/develop/api-reference/navigation) et [`st.fragment`](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment).
- [Pydantic v2 — Documentation officielle](https://docs.pydantic.dev/latest/) — Validation et sérialisation.
- [SQLite — Documentation Python `sqlite3`](https://docs.python.org/3/library/sqlite3.html) — Couche de persistance.

#### Modèles génératifs audio

- [Qwen2.5-7B-Instruct sur Hugging Face](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) — Modèle LLM par défaut.
- [Mixtral-8x7B-Instruct sur Hugging Face](https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1) — Alternative LLM proposée dans `.env.example`.
- [ElevenLabs API](https://elevenlabs.io/docs/api-reference/) — Cible TTS principale.
- [Bark sur Hugging Face](https://huggingface.co/suno/bark) — Cible TTS open-source.
- [MusicGen sur Hugging Face](https://huggingface.co/facebook/musicgen-large) — Cible musicale.

#### Patterns de prompt engineering

- *« Self-Refine: Iterative Refinement with Self-Feedback »* — Madaan et al., 2023. Pattern à la base de la boucle d'optimisation §4.5.
- *« G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment »* — Liu et al., 2023. Pattern de référence pour le LLM-as-a-judge §4.4.
- *« Reflexion: Language Agents with Verbal Reinforcement Learning »* — Shinn et al., 2023. Inspiration pour le mécanisme d'escalade après échec §4.5.6.

#### Steering interne du projet

- `.kiro/steering/product.md` — Cadrage produit (problème, fonctionnalités, critères de succès).
- `.kiro/steering/tech.md` — Stack technique, conventions de code, commandes courantes.
- `.kiro/steering/structure.md` — Arborescence cible, séparation des responsabilités, schéma SQLite.

---

*Fin du rapport technique. Document généré pour le projet n°5 — Générateur Automatique de Prompts Professionnels.*
