"""
╔══════════════════════════════════════════════════════════════════╗
║   STUDIO ANIMÉ ÉDUCATIF — Version Professionnelle               ║
║   Streamlit + Groq API (GRATUIT) · Thème clair                  ║
║   Étapes : Écrire → Valider IA → Scénario → Vidéo              ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import subprocess, sys, os, re, math, random, asyncio, json, tempfile
from dataclasses import dataclass
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════
#  INSTALLATION DES DÉPENDANCES
# ══════════════════════════════════════════════════════════
@st.cache_resource
def install_deps():
    deps = [
        "groq",
        "edge-tts",
        "gtts",
        "pydub",
        "opencv-python-headless",
        "pillow",
        "numpy"
    ]
    for pkg in deps:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", pkg],
            capture_output=True
        )
    return True

install_deps()

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

try:
    from groq import Groq as _GroqClient
    _GROQ_OK = True
except ImportError:
    _GROQ_OK = False

try:
    import edge_tts
    _EDGE_TTS_OK = True
except ImportError:
    _EDGE_TTS_OK = False


# ══════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════
class Config:
    FPS          = 24
    SIZE         = 512
    CRF          = 23
    EASE_FRAMES  = 6
    FONT_DIR     = "/usr/share/fonts/truetype/dejavu/"
    FONT_BOLD    = FONT_DIR + "DejaVuSans-Bold.ttf"
    FONT_REGULAR = FONT_DIR + "DejaVuSans.ttf"
    VOICE_FILLE  = "fr-FR-DeniseNeural"
    VOICE_GARCON = "fr-FR-HenriNeural"
    VOICE_RATE   = "-20%"
    VOICE_PITCH  = "+5Hz"
    AI_MODEL     = "llama-3.1-8b-instant"


# ══════════════════════════════════════════════════════════
#  THÈME STREAMLIT CLAIR
# ══════════════════════════════════════════════════════════
def apply_light_theme():
    st.markdown("""
    <style>
    /* ── Fond général blanc/gris clair ── */
    .stApp, .stApp > div, [data-testid="stAppViewContainer"] {
        background-color: #f5f7fa !important;
    }
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    .block-container {
        background-color: transparent !important;
        padding-top: 2rem !important;
        max-width: 860px !important;
    }

    /* ── Typographie ── */
    html, body, .stApp, p, div, span, label {
        color: #1e293b !important;
        font-family: 'Segoe UI', system-ui, sans-serif !important;
    }
    h1, h2, h3 { color: #0f172a !important; }

    /* ── Cartes / conteneurs blancs ── */
    .anime-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }

    /* ── En-tête héro ── */
    .hero-banner {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        border-radius: 20px;
        padding: 2rem 2rem 1.75rem;
        text-align: center;
        margin-bottom: 1.5rem;
        color: white !important;
    }
    .hero-banner h1 {
        color: white !important;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0 0 8px !important;
    }
    .hero-banner p {
        color: rgba(255,255,255,0.88) !important;
        font-size: 1rem;
        margin: 0 !important;
    }

    /* ── Badges étapes ── */
    .step-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 99px;
        padding: 6px 14px;
        font-size: 0.82rem;
        font-weight: 700;
        color: #475569;
        margin-bottom: 1rem;
    }
    .step-badge.active {
        background: #ede9fe;
        border-color: #8b5cf6;
        color: #6d28d9;
    }
    .step-badge.done {
        background: #dcfce7;
        border-color: #86efac;
        color: #166534;
    }

    /* ── Stepper visuel ── */
    .stepper-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .step-circle {
        width: 38px; height: 38px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 15px;
        border: 2px solid #cbd5e1;
        background: #f8fafc;
        color: #94a3b8;
        position: relative; z-index: 1;
    }
    .step-circle.sc-active {
        background: #6366f1; border-color: #6366f1;
        color: white; box-shadow: 0 0 0 4px rgba(99,102,241,0.15);
    }
    .step-circle.sc-done {
        background: #22c55e; border-color: #22c55e; color: white;
    }
    .step-connector {
        width: 48px; height: 2px;
        background: #e2e8f0; margin-bottom: 18px;
    }
    .step-connector.sc-done { background: #22c55e; }
    .step-txt {
        font-size: 11px; font-weight: 700;
        text-align: center; width: 74px;
        color: #94a3b8 !important; margin-top: 4px;
    }
    .step-txt.sc-active { color: #6366f1 !important; }
    .step-txt.sc-done   { color: #16a34a !important; }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 10px !important;
        color: #1e293b !important;
        font-size: 0.95rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
    }

    /* ── Boutons ── */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.65rem 1.5rem !important;
        transition: all 0.2s !important;
        box-shadow: 0 3px 12px rgba(99,102,241,0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99,102,241,0.4) !important;
    }
    .stButton > button[kind="secondary"] {
        background: #f1f5f9 !important;
        color: #475569 !important;
        box-shadow: none !important;
        border: 1.5px solid #cbd5e1 !important;
    }

    /* ── Boîte de validation ── */
    .val-ok {
        background: #f0fdf4; border: 1.5px solid #86efac;
        border-radius: 14px; padding: 1.25rem;
    }
    .val-warn {
        background: #fff7ed; border: 1.5px solid #fed7aa;
        border-radius: 14px; padding: 1.25rem;
    }
    .val-error {
        background: #fef2f2; border: 1.5px solid #fca5a5;
        border-radius: 14px; padding: 1.25rem;
    }

    /* ── Carte personnage ── */
    .char-card {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 14px; padding: 1rem;
        display: flex; gap: 14px; align-items: center;
        margin: 0.75rem 0;
    }

    /* ── Partie chanson ── */
    .song-part {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 10px; padding: 0.875rem 1rem;
        margin-bottom: 8px;
    }
    .song-part-label {
        font-size: 0.72rem; font-weight: 800;
        color: #6366f1; text-transform: uppercase;
        letter-spacing: 0.05em; margin-bottom: 4px;
    }
    .song-part-text {
        font-size: 0.88rem; color: #475569;
        line-height: 1.6; font-style: italic;
    }

    /* ── Thème décor ── */
    .theme-chip {
        display: inline-flex; align-items: center; gap: 6px;
        background: #ede9fe; border: 1px solid #c4b5fd;
        border-radius: 99px; padding: 4px 12px;
        font-size: 0.82rem; font-weight: 700; color: #5b21b6;
        margin: 4px 4px 0 0;
    }

    /* ── Progress bar custom ── */
    .prog-wrap { margin: 10px 0; }
    .prog-label {
        display: flex; justify-content: space-between;
        font-size: 0.82rem; font-weight: 700;
        color: #475569; margin-bottom: 4px;
    }
    .prog-bg {
        height: 8px; background: #e2e8f0;
        border-radius: 99px; overflow: hidden;
    }
    .prog-fill {
        height: 100%;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        border-radius: 99px;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        color: #374151 !important;
        font-weight: 700 !important;
    }

    /* ── Alertes ── */
    .stAlert { border-radius: 12px !important; }

    /* ── Info box ── */
    .info-note {
        background: #eff6ff; border: 1px solid #bfdbfe;
        border-radius: 10px; padding: 10px 14px;
        font-size: 0.84rem; color: #1d4ed8;
        margin: 8px 0;
    }

    /* ── Grille exemples ── */
    .ex-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }

    /* ── Divider ── */
    hr { border-color: #e2e8f0 !important; }

    /* ── Masquer branding Streamlit ── */
    #MainMenu, footer, header { visibility: hidden; }

    /* ══ Étiquettes section ══ */
    .section-title {
        font-size: 1.1rem; font-weight: 800;
        color: #1e293b; margin: 0 0 0.75rem;
        display: flex; align-items: center; gap: 8px;
    }
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  DATACLASSES
# ══════════════════════════════════════════════════════════
@dataclass
class Character:
    prenom: str
    age: int
    genre: str

@dataclass
class SongData:
    titre: str
    intro: str
    acte1: str
    acte2: str
    refrain1: str
    acte3: str
    acte4: str
    refrain2: str
    acte5: str
    acte6: str
    outro: str

@dataclass
class Scene:
    titre: str
    acte_label: str
    decor: str
    action: str
    emotion: str
    dialogue: str
    duree: int
    sky_mood: str = "day"
    song_part: str = ""


# ══════════════════════════════════════════════════════════
#  DONNÉES DES THÈMES VISUELS
# ══════════════════════════════════════════════════════════
THEMES = {
    "electric": {
        "label": "⚡ Électricité",
        "emoji": "⚡",
        "color_primary": "#6366f1",
        "sky_normal": ((100, 140, 255), (180, 210, 255)),
        "sky_danger": ((180, 60,  40), (120, 40, 30)),
        "sky_golden": ((255, 160, 40), (255, 200, 100)),
        "ground":     (60, 160, 60),
        "ground_s":   (40, 120, 40),
        "fx_color":   (80, 200, 255),    # éclairs bleus
        "wall":       (240, 240, 255),   # maison tech
        "description": "Maison moderne, prises électriques, éclairs bleus",
    },
    "kitchen": {
        "label": "🍳 Cuisine",
        "emoji": "🍳",
        "color_primary": "#f97316",
        "sky_normal": ((255, 220, 150), (255, 240, 180)),
        "sky_danger": ((200, 80,  20), (140, 50, 10)),
        "sky_golden": ((255, 180, 60), (255, 220, 100)),
        "ground":     (100, 70,  40),
        "ground_s":   (70,  50,  25),
        "fx_color":   (255, 120, 0),     # flammes orange
        "wall":       (255, 230, 200),   # cuisine chaleureuse
        "description": "Grande cuisine familiale, couteaux, flammes orange",
    },
    "meds": {
        "label": "💊 Médicaments",
        "emoji": "💊",
        "color_primary": "#a855f7",
        "sky_normal": ((200, 180, 255), (230, 220, 255)),
        "sky_danger": ((120, 40,  160), (80,  20, 120)),
        "sky_golden": ((220, 180, 255), (240, 210, 255)),
        "ground":     (80,  160, 80),
        "ground_s":   (55,  120, 55),
        "fx_color":   (200, 100, 255),   # bulles violettes
        "wall":       (240, 230, 255),   # salle de bain
        "description": "Salle de bain, armoire à pharmacie, lumière violette",
    },
    "pool": {
        "label": "🏊 Piscine / Eau",
        "emoji": "🏊",
        "color_primary": "#0ea5e9",
        "sky_normal": ((60,  160, 255), (150, 210, 255)),
        "sky_danger": ((20,  60,  140), (10,  40, 100)),
        "sky_golden": ((255, 200, 80), (255, 230, 130)),
        "ground":     (0,   120, 200),   # eau
        "ground_s":   (0,   90,  160),
        "fx_color":   (100, 220, 255),   # vagues bleues
        "wall":       (200, 240, 255),   # bord de piscine
        "description": "Piscine extérieure, eau bleue, carrelage blanc",
    },
    "road": {
        "label": "🚦 Route / Rue",
        "emoji": "🚦",
        "color_primary": "#64748b",
        "sky_normal": ((140, 180, 230), (190, 215, 245)),
        "sky_danger": ((160, 80,  40), (120, 60, 30)),
        "sky_golden": ((255, 180, 60), (255, 210, 110)),
        "ground":     (80,  80,  80),    # bitume gris
        "ground_s":   (55,  55,  55),
        "fx_color":   (255, 255, 0),     # lignes jaunes route
        "wall":       (200, 200, 210),   # bâtiments gris
        "description": "Rue de ville, passage piéton, feux de signalisation",
    },
    "fire": {
        "label": "🔥 Feu / Gaz",
        "emoji": "🔥",
        "color_primary": "#ef4444",
        "sky_normal": ((255, 180, 100), (255, 210, 150)),
        "sky_danger": ((200, 50,  0),   (140, 30, 0)),
        "sky_golden": ((255, 160, 40), (255, 200, 90)),
        "ground":     (70,  160, 70),
        "ground_s":   (50,  120, 50),
        "fx_color":   (255, 80,  0),     # flammes rouges
        "wall":       (255, 220, 195),   # cuisine/barbecue
        "description": "Cuisine avec gaz, flammes rouges dramatiques, BBQ",
    },
    "general": {
        "label": "🌟 Général",
        "emoji": "🌟",
        "color_primary": "#6366f1",
        "sky_normal": ((100, 160, 255), (200, 230, 255)),
        "sky_danger": ((220, 80,  50), (150, 60, 40)),
        "sky_golden": ((255, 180, 60), (255, 220, 120)),
        "ground":     (70,  175, 70),
        "ground_s":   (50,  130, 50),
        "fx_color":   (255, 200, 0),
        "wall":       (255, 235, 210),
        "description": "Environnement général coloré et adapté",
    },
}

EXAMPLES = [
    {"icon": "⚡", "label": "Prises électriques",  "text": "Mon fils Adam, 5 ans, touche les prises électriques avec ses doigts",     "theme": "electric"},
    {"icon": "🔪", "label": "Couteaux de cuisine", "text": "Mon fils Youssef, 7 ans, joue avec les couteaux de cuisine",               "theme": "kitchen"},
    {"icon": "💊", "label": "Médicaments",          "text": "Ma fille Inès, 6 ans, mange des médicaments dans l'armoire à pharmacie",  "theme": "meds"},
    {"icon": "🏊", "label": "Bord de piscine",      "text": "Ma fille Lina, 4 ans, s'approche seule du bord de la piscine",           "theme": "pool"},
    {"icon": "🚗", "label": "Traverser la rue",     "text": "Mon fils Rayan, 6 ans, traverse la rue sans regarder",                   "theme": "road"},
    {"icon": "🔥", "label": "Flamme / gaz",         "text": "Ma fille Sara, 5 ans, allume les boutons du gaz de la cuisine",          "theme": "fire"},
]


# ══════════════════════════════════════════════════════════
#  PROMPTS IA
# ══════════════════════════════════════════════════════════
VALIDATION_PROMPT = """Tu es un modérateur pour une application éducative pour enfants de 3 à 8 ans.
Un parent envoie une phrase décrivant la bêtise dangereuse de son enfant pour créer un dessin animé éducatif.

Analyse cette phrase et réponds UNIQUEMENT en JSON valide, sans markdown, sans explication :
{
  "valide": true,
  "raison": "explication courte",
  "prenom": "prénom extrait ou null",
  "age": 5,
  "genre": "garçon ou fille",
  "danger": "type de danger en 3 mots max",
  "theme": "electric|kitchen|meds|pool|road|fire|general",
  "suggestions": ["suggestion 1 si non valide", "suggestion 2 si non valide"],
  "message_parent": "message bienveillant de 2 phrases pour le parent"
}

Valide = true UNIQUEMENT si c'est une bêtise dangereuse normale d'enfant liée à la sécurité.
Valide = false si contenu violent, inapproprié, ou sans rapport avec la sécurité enfant.

Phrase du parent : {betise}"""

SCENARIO_PROMPT = """Tu es un auteur de livres éducatifs pour enfants de 3 à 8 ans.
Un parent décrit une bêtise dangereuse de son enfant pour créer un dessin animé éducatif.

Génère une chanson narrative complète avec des rimes en français.
Le décor doit correspondre exactement au type de danger : {theme_description}

Réponds UNIQUEMENT en JSON valide, sans markdown :
{{
  "prenom": "prénom de l'enfant",
  "age": 5,
  "genre": "garçon ou fille",
  "danger_court": "3 mots max",
  "decor_principal": "description du décor en 8 mots",
  "ambiance_couleur": "couleur dominante (ex: bleu électrique, orange feu)",
  "song": {{
    "titre": "La Chanson de [prénom] et [danger]",
    "intro": "2-3 phrases d'accroche musicale avec rimes",
    "acte1": "Vie normale joyeuse (3-4 phrases rimées)",
    "acte2": "Il découvre l'objet dangereux (3-4 phrases rimées)",
    "refrain1": "Refrain d'avertissement NON NON NON (3-4 phrases rimées)",
    "acte3": "Il commet la bêtise malgré tout (2-3 phrases dramatiques)",
    "acte4": "La conséquence terrible arrive (3-4 phrases rimées)",
    "refrain2": "Refrain de la leçon avec la bonne solution (3-4 phrases rimées)",
    "acte5": "Il comprend et pleure (3-4 phrases émouvantes)",
    "acte6": "Il fait une promesse solennelle (3-4 phrases rimées)",
    "outro": "Message direct bienveillant à l'enfant spectateur (2-3 phrases)"
  }}
}}

Phrase du parent : {betise}"""


# ══════════════════════════════════════════════════════════
#  FONCTIONS IA — GROQ API (GRATUIT)
# ══════════════════════════════════════════════════════════
def call_groq(api_key: str, prompt: str, max_tokens: int = 1000) -> str:
    """Appelle l'API Groq et retourne le texte brut."""
    client = _GroqClient(api_key=api_key)
    message = client.chat.completions.create(
        model=Config.AI_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw


def validate_with_ai(betise: str, api_key: str) -> dict:
    """Étape 1 : Validation du contenu par l'IA."""
    prompt = VALIDATION_PROMPT.replace("{betise}", betise)
    raw = call_groq(api_key, prompt, max_tokens=600)
    return json.loads(raw)


def generate_scenario(betise: str, theme: str, api_key: str) -> dict:
    """Étape 2 : Génération du scénario complet."""
    theme_info = THEMES.get(theme, THEMES["general"])
    prompt = SCENARIO_PROMPT.format(
        betise=betise,
        theme_description=theme_info["description"]
    )
    raw = call_groq(api_key, prompt, max_tokens=2500)
    return json.loads(raw)


def parse_scenario(data: dict) -> tuple:
    """Parse les données JSON en objets Character + SongData."""
    char = Character(
        prenom=data.get("prenom", ""),
        age=int(data.get("age", 5)),
        genre=data.get("genre", "garçon")
    )
    s = data["song"]
    song = SongData(
        titre=s.get("titre", ""),
        intro=s.get("intro", ""),
        acte1=s.get("acte1", ""),
        acte2=s.get("acte2", ""),
        refrain1=s.get("refrain1", ""),
        acte3=s.get("acte3", ""),
        acte4=s.get("acte4", ""),
        refrain2=s.get("refrain2", ""),
        acte5=s.get("acte5", ""),
        acte6=s.get("acte6", ""),
        outro=s.get("outro", "")
    )
    return char, song


# ══════════════════════════════════════════════════════════
#  CONSTRUCTION DES SCÈNES
# ══════════════════════════════════════════════════════════
def build_scenes(char: Character, song: SongData, theme_key: str) -> List[Scene]:
    p = char.prenom
    f = Config.FPS
    t = THEMES.get(theme_key, THEMES["general"])

    # Décors spécifiques selon le thème
    decor_map = {
        "electric": ["maison", "parc",   "maison", "maison", "maison", "danger",
                     "parc",   "parc",   "parc",   "parc",   "parc",   "parc",
                     "parc",   "parc",   "parc"],
        "kitchen":  ["maison", "parc",   "maison", "maison", "maison", "danger",
                     "parc",   "parc",   "parc",   "parc",   "parc",   "parc",
                     "parc",   "parc",   "parc"],
        "pool":     ["parc",   "parc",   "parc",   "danger", "danger", "danger",
                     "parc",   "parc",   "parc",   "parc",   "parc",   "parc",
                     "parc",   "parc",   "parc"],
        "road":     ["parc",   "parc",   "parc",   "danger", "danger", "danger",
                     "parc",   "parc",   "parc",   "parc",   "parc",   "parc",
                     "parc",   "parc",   "parc"],
    }
    decors = decor_map.get(theme_key, ["parc"] * 15)

    return [
        Scene("Introduction",       "Intro",      decors[0],  "saute_joie",       "heureux",    f"La chanson de {p} !",          f*5, "day",    "intro"),
        Scene("La vie de " + p,     "Acte I",     decors[1],  "court_vite",       "heureux",    f"{p} joue et rit !",            f*5, "day",    "acte1"),
        Scene("Une belle journée",  "Acte I",     decors[2],  "marche_content",   "heureux",    f"{p} est heureux.",             f*4, "golden", "acte1"),
        Scene("Qu'est-ce que c'est ?","Acte II",  decors[3],  "decouvre_surpris", "curieux",    f"Quelque chose attire {p}...",  f*5, "golden", "acte2"),
        Scene("Une idée...",        "Acte II",    decors[4],  "hesite_balance",   "penseur",    f"Juste une petite fois...",     f*4, "golden", "acte2"),
        Scene("⚠️ ATTENTION !",     "Refrain",    decors[5],  "appelle_gestes",   "effraye",    f"Non non non ! Danger !",       f*5, "day",    "refrain1"),
        Scene("NON NON NON !",      "Refrain",    decors[6],  "saute_peur",       "effraye",    f"Appelle un adulte !",          f*4, "day",    "refrain1"),
        Scene("La bêtise !",        "Acte III",   decors[7],  "fait_betise_saute","curieux",    f"{p} n'écoute pas !",          f*6, "dusk",   "acte3"),
        Scene("Conséquences !",     "Acte IV",    decors[8],  "court_panique",    "effraye",    f"{p} a très peur !",           f*6, "dusk",   "acte4"),
        Scene("AU SECOURS !",       "Acte IV",    decors[9],  "appelle_gestes",   "effraye",    "MAMAN ! PAPA !",               f*5, "dusk",   "acte4"),
        Scene("La leçon",           "Refrain",    decors[10], "ecoute_hoche",     "desole",     f"Voilà ce qu'il faut faire.",  f*5, "day",    "refrain2"),
        Scene(f"{p} comprend",      "Acte V",     decors[11], "pleure_assise",    "triste",     f"{p} pleure et comprend.",     f*6, "day",    "acte5"),
        Scene("La promesse",        "Acte VI",    decors[12], "saute_promesse",   "determine",  f"{p} fait une promesse !",     f*5, "day",    "acte6"),
        Scene("Et toi ?",           "Outro",      decors[13], "pointe_enfant",    "heureux",    f"{p} te parle à toi !",        f*5, "day",    "outro"),
        Scene("À bientôt !",        "Outro",      decors[14], "salue_saute",      "fier",       f"Bravo d'avoir regardé !",     f*4, "day",    "outro"),
    ]


# ══════════════════════════════════════════════════════════
#  RENDU VIDÉO — PALETTE & HELPERS
# ══════════════════════════════════════════════════════════
class P:
    SKIN   = (255, 232, 205); CHEEK  = (255, 175, 165)
    HAIR_B = (55,  38,  18);  HAIR_G = (195, 135, 70)
    SHIRT_B= (70,  130, 255); SHIRT_G= (255, 120, 175)
    PANTS  = (45,  85,  195); SHOE   = (175, 48,  48)
    EYE_B  = (80,  160, 255); EYE_G  = (255, 100, 195)
    WHITE  = (255, 255, 255); OUTLINE= (30,  20,  10)
    SUN    = (255, 245, 100); TEAR   = (90,  195, 255)
    FLAME_O= (255, 110, 0);   FLAME_C= (255, 230, 80)
    ROOF   = (185, 80,  60);  DOOR   = (110, 65,  35)
    WINDOW = (180, 220, 255); TREE_T = (85,  52,  28)
    TREE_L = (60,  185, 60);  GRASS2 = (60,  185, 60)
    UI_BG  = (240, 244, 252)  # clair !
    UI_TFG = (30,  30,  80);  UI_DFG = (60,  60,  140)
    SONG_BG= (245, 245, 255); SONG_FG= (80,  60,  180)
    UI_BAR = (99,  102, 241)


def lerp(a, b, t): return a + (b - a) * t
def lc(c1, c2, t): return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def grad(draw, x0, y0, x1, y1, tc, bc):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0)
        draw.line([(x0, y), (x1, y)], fill=lc(tc, bc, t))


def get_sky(theme_data: dict, mood: str) -> tuple:
    if mood == "dusk":   return theme_data["sky_danger"]
    if mood == "golden": return theme_data["sky_golden"]
    return theme_data["sky_normal"]


def draw_bg(draw, decor: str, mood: str, frame: int, theme_data: dict):
    S = Config.SIZE
    tc, bc = get_sky(theme_data, mood)
    grad(draw, 0, 0, S, int(S * .64), tc, bc)

    # Soleil
    if mood != "dusk":
        sx, sy = int(S * .85), int(S * .09)
        draw.ellipse([sx-22, sy-22, sx+22, sy+22], fill=P.SUN)
        for ang in range(0, 360, 45):
            rx = sx + int(30 * math.cos(math.radians(ang + frame * .3)))
            ry = sy + int(30 * math.sin(math.radians(ang + frame * .3)))
            draw.line([(sx, sy), (rx, ry)], fill=P.SUN, width=2)

    # Sol thématique
    gnd   = theme_data["ground"]
    gnd_s = theme_data["ground_s"]
    gnd_color = gnd_s if mood == "dusk" else gnd
    draw.rectangle([0, int(S * .64), S, S], fill=gnd_color)

    # Nuages
    if mood != "dusk":
        for i in range(4):
            cx2 = (50 + i * int(S / 4) + int(3 * math.sin(frame * .015 + i * 1.2))) % S
            cy2 = int(S * .12) + i % 2 * int(S * .06)
            for dx in [-16, 0, 16]:
                draw.ellipse([cx2 + dx - 14, cy2 - 12, cx2 + dx + 14, cy2 + 12], fill=P.WHITE)

    # Arbre
    tx, ty = int(S * .83), int(S * .64)
    draw.rectangle([tx - 8, ty - int(S * .22), tx + 8, ty], fill=P.TREE_T)
    draw.ellipse([tx - int(S * .09), ty - int(S * .32),
                  tx + int(S * .09), ty - int(S * .16)], fill=P.TREE_L)

    # Maison / décor thématique
    if decor in ("maison", "danger"):
        wall_color = theme_data.get("wall", P.WHITE)
        mx, my = 28, int(S * .62)
        mw, mh = int(S * .30), int(S * .22)
        draw.rectangle([mx, my - mh, mx + mw, my],
                       fill=wall_color, outline=P.OUTLINE, width=2)
        draw.polygon([mx - 10, my - mh,
                      mx + mw // 2, my - mh - int(S * .10),
                      mx + mw + 10, my - mh],
                     fill=P.ROOF, outline=P.OUTLINE, width=2)
        draw.rectangle([mx + mw // 2 - 15, my - int(S * .10),
                        mx + mw // 2 + 15, my],
                       fill=P.DOOR, outline=P.OUTLINE, width=2)
        wl = (255, 255, 180) if mood == "dusk" else P.WINDOW
        for wx2 in [mx + 8, mx + mw - 38]:
            draw.rectangle([wx2, my - int(S * .17), wx2 + 30, my - int(S * .10)],
                           fill=wl, outline=P.OUTLINE, width=2)

        # Effet spécifique au thème dans la maison
        fx_c = theme_data["fx_color"]
        if mood == "dusk":
            for fi in range(5):
                fh2 = 28 + int(16 * math.sin(frame * .22 + fi * .8))
                fx2 = mx + 10 + fi * int(mw / 5)
                draw.ellipse([fx2 - 8, my - mh - fh2, fx2 + 8, my - mh],
                             fill=(*fx_c[:2], max(0, fx_c[2] - 30)) if len(fx_c) >= 3 else fx_c)
                draw.ellipse([fx2 - 4, my - mh - fh2 - 8, fx2 + 4, my - mh - 6],
                             fill=P.FLAME_C)

    # Effets spéciaux thème dans le décor "danger"
    if decor == "danger":
        fx_c = theme_data["fx_color"]
        for i in range(6):
            angle = math.radians(i * 60 + frame * 3)
            ex2 = int(S * .5) + int(80 * math.cos(angle))
            ey2 = int(S * .45) + int(50 * math.sin(angle))
            r = 6 + int(4 * math.sin(frame * .18 + i))
            draw.ellipse([ex2 - r, ey2 - r, ex2 + r, ey2 + r], fill=fx_c)


def anim_off(action: str, frame: int) -> tuple:
    if action in ("saute_joie", "saute_promesse", "salue_saute", "fait_betise_saute"):
        return 0, -abs(int(30 * math.sin(frame * .16)))
    if action == "saute_peur":
        return int(4 * math.sin(frame * .45)), -abs(int(18 * math.sin(frame * .32)))
    if action in ("court_vite", "marche_content", "court_panique"):
        return int(5 * math.sin(frame * .12)), int(5 * math.sin(frame * .22))
    if action == "pleure_assise":
        return 0, int(Config.SIZE * .04)
    return 0, int(3 * math.sin(frame * .07))


def draw_char(draw, cx: int, cy: int, action: str, emotion: str,
              frame: int, genre: str):
    S = Config.SIZE
    dx, dy = anim_off(action, frame)
    x, y = cx + dx, cy + dy

    shirt = P.SHIRT_G if genre == "fille" else P.SHIRT_B
    hair  = P.HAIR_G  if genre == "fille" else P.HAIR_B
    eye_c = P.EYE_G   if genre == "fille" else P.EYE_B

    # Ombre au sol
    draw.ellipse([cx - int(S * .06), cy + int(S * .015),
                  cx + int(S * .06), cy + int(S * .03)],
                 fill=(0, 0, 0, 80) if hasattr(draw, '_image') else (30, 30, 30))

    if emotion == "triste":    shirt = lc(shirt, (130, 130, 160), .4)
    elif emotion == "effraye": shirt = lc(shirt, (180, 180, 190), .35)

    # Corps
    draw.ellipse([x - int(S * .05), y - int(S * .04),
                  x + int(S * .05), y + int(S * .075)],
                 fill=shirt, outline=P.OUTLINE, width=2)

    # Jambes
    if action == "pleure_assise":
        draw.ellipse([x - int(S * .06), y + int(S * .07),
                      x + int(S * .01), y + int(S * .13)],
                     fill=P.PANTS, outline=P.OUTLINE, width=2)
        draw.ellipse([x + int(S * .01), y + int(S * .07),
                      x + int(S * .06), y + int(S * .13)],
                     fill=P.PANTS, outline=P.OUTLINE, width=2)
    else:
        sw = int(20 * math.sin(frame * .2)) if action in (
            "court_vite", "marche_content", "court_panique") else 3
        draw.line([x - int(S * .02), y + int(S * .065),
                   x - int(S * .03) - sw, y + int(S * .12)],
                  fill=P.PANTS, width=int(S * .022))
        draw.line([x + int(S * .02), y + int(S * .065),
                   x + int(S * .03) + sw, y + int(S * .12)],
                  fill=P.PANTS, width=int(S * .022))
        draw.ellipse([x - int(S * .05) - sw, y + int(S * .11),
                      x - int(S * .01) - sw, y + int(S * .135)],
                     fill=P.SHOE, outline=P.OUTLINE, width=2)
        draw.ellipse([x + int(S * .01) + sw, y + int(S * .11),
                      x + int(S * .05) + sw, y + int(S * .135)],
                     fill=P.SHOE, outline=P.OUTLINE, width=2)

    # Bras
    skin = P.SKIN
    def arm(x1, y1, x2, y2):
        draw.line([x1, y1, x2, y2], fill=skin, width=int(S * .018))
        draw.ellipse([x2 - 5, y2 - 5, x2 + 5, y2 + 5],
                     fill=skin, outline=P.OUTLINE, width=1)

    sw2 = int(22 * math.sin(frame * .18))
    if action == "saute_joie":
        arm(x - int(S * .046), y - int(S * .008), x - int(S * .084), y - int(S * .078))
        arm(x + int(S * .046), y - int(S * .008), x + int(S * .084), y - int(S * .078))
    elif action in ("court_vite", "marche_content", "court_panique"):
        arm(x - int(S * .046), y, x - int(S * .07) + sw2, y + int(S * .022))
        arm(x + int(S * .046), y, x + int(S * .07) - sw2, y + int(S * .022))
    elif action == "appelle_gestes":
        gh = int(30 * math.sin(frame * .16))
        arm(x - int(S * .046), y, x - int(S * .09), y - int(S * .062) - gh)
        arm(x + int(S * .046), y, x + int(S * .09), y - int(S * .062) + gh)
    elif action == "saute_peur":
        t2 = int(6 * math.sin(frame * .45))
        arm(x - int(S * .046), y + t2, x - int(S * .075), y - int(S * .05) + t2)
        arm(x + int(S * .046), y - t2, x + int(S * .075), y - int(S * .05) - t2)
    elif action == "pointe_enfant":
        arm(x - int(S * .046), y, x - int(S * .06), y + int(S * .022))
        draw.line([x + int(S * .046), y, x + int(S * .1), y - int(S * .02)],
                  fill=skin, width=int(S * .018))
        draw.ellipse([x + int(S * .094), y - int(S * .035),
                      x + int(S * .116), y - int(S * .013)],
                     fill=skin, outline=P.OUTLINE, width=1)
    elif action in ("saute_promesse", "salue_saute"):
        arm(x - int(S * .046), y, x - int(S * .06), y + int(S * .025))
        arm(x + int(S * .046), y, x + int(S * .08), y - int(S * .086))
    elif action == "fait_betise_saute":
        arm(x - int(S * .046), y, x - int(S * .07), y - int(S * .03))
        arm(x + int(S * .046), y, x + int(S * .086), y - int(S * .04))
    elif action == "pleure_assise":
        arm(x - int(S * .046), y + int(S * .034), x - int(S * .025), y + int(S * .066))
        arm(x + int(S * .046), y + int(S * .034), x + int(S * .025), y + int(S * .066))
    elif action == "decouvre_surpris":
        arm(x + int(S * .046), y, x + int(S * .084), y + int(S * .005))
        arm(x - int(S * .046), y, x - int(S * .06), y + int(S * .025))
    else:
        arm(x - int(S * .046), y, x - int(S * .062), y + int(S * .022))
        arm(x + int(S * .046), y, x + int(S * .062), y + int(S * .022))

    # Tête
    hy = y - int(S * .13)
    draw.ellipse([x - int(S * .066), hy,
                  x + int(S * .066), hy + int(S * .136)],
                 fill=P.SKIN, outline=P.OUTLINE, width=2)
    draw.arc([x - int(S * .064), hy, x + int(S * .064), hy + int(S * .07)],
             180, 0, fill=hair, width=10)
    if genre == "fille":
        draw.rectangle([x - int(S * .07), hy + int(S * .012),
                        x - int(S * .042), hy + int(S * .094)], fill=hair)
        draw.rectangle([x + int(S * .042), hy + int(S * .012),
                        x + int(S * .07), hy + int(S * .094)], fill=hair)

    # Yeux
    ey = hy + int(S * .054)
    ew, eh = 14, 12
    if emotion in ("surpris", "effraye"):   eh = 16
    elif emotion in ("heureux", "fier"):    eh = 10
    cligne = (frame % 75) < 3
    for side in (-1, 1):
        ox = x + side * int(S * .034)
        if cligne:
            draw.arc([ox - ew, ey - 3, ox + ew, ey + 5], 0, 180,
                     fill=P.OUTLINE, width=2)
        else:
            draw.ellipse([ox - ew, ey - eh, ox + ew, ey + eh],
                         fill=P.WHITE, outline=P.OUTLINE, width=2)
            draw.ellipse([ox - 6, ey - 5, ox + 6, ey + 5], fill=eye_c)
            draw.ellipse([ox - 4, ey - 3, ox + 4, ey + 3], fill=(8, 8, 18))
            draw.ellipse([ox - 10, ey - 8, ox - 3, ey - 2], fill=P.WHITE)

    # Joues
    draw.ellipse([x - int(S * .076), ey + 5, x - int(S * .044), ey + 20],
                 fill=P.CHEEK)
    draw.ellipse([x + int(S * .044), ey + 5, x + int(S * .076), ey + 20],
                 fill=P.CHEEK)

    # Bouche
    my2 = hy + int(S * .096)
    if emotion in ("heureux", "fier", "determine"):
        draw.arc([x - 10, my2 - 5, x + 10, my2 + 8], 0, 180,
                 fill=(185, 65, 65), width=3)
    elif emotion in ("triste", "desole"):
        draw.arc([x - 10, my2 + 5, x + 10, my2 + 14], 180, 0,
                 fill=(178, 65, 65), width=3)
    elif emotion in ("surpris", "effraye"):
        draw.ellipse([x - 9, my2 - 2, x + 9, my2 + 14], fill=(135, 48, 48))
    else:
        draw.line([x - 7, my2 + 6, x + 7, my2 + 6], fill=(168, 68, 68), width=2)

    # Larmes
    if emotion == "triste":
        for s2 in (-1, 1):
            lx = x + s2 * int(S * .056)
            ly = ey + int(S * .025) + int(5 * math.sin(frame * .22 + s2))
            draw.polygon([lx - 4, ly, lx + 4, ly, lx, ly + 14], fill=P.TEAR)

    # Lignes de vitesse
    if action in ("court_vite", "court_panique"):
        for li in range(4):
            lx2 = x - int(S * .12) - li * 10
            ly2 = y + li * 6
            draw.line([lx2, ly2, lx2 + int(S * .044), ly2],
                      fill=(160, 165, 190), width=2)


# ══════════════════════════════════════════════════════════
#  POLICES
# ══════════════════════════════════════════════════════════
_FONTS = None

def get_fonts():
    global _FONTS
    if _FONTS:
        return _FONTS
    S = Config.SIZE
    try:
        _FONTS = {
            "big":   ImageFont.truetype(Config.FONT_BOLD,    max(16, S // 20)),
            "med":   ImageFont.truetype(Config.FONT_BOLD,    max(13, S // 28)),
            "small": ImageFont.truetype(Config.FONT_REGULAR, max(12, S // 32)),
        }
    except Exception:
        d = ImageFont.load_default()
        _FONTS = {"big": d, "med": d, "small": d}
    return _FONTS


def song_line(song: SongData, part: str) -> str:
    text = getattr(song, part, "")
    for sep in ["...", "!", "."]:
        idx = text.find(sep)
        if idx > 15:
            return text[:idx].strip()
    return text[:48].strip()


def draw_ui(img: Image.Image, scene: Scene, f_in_scene: int,
            song: SongData, genre: str):
    """Interface HUD — fond clair, texte foncé."""
    draw = ImageDraw.Draw(img)
    F = get_fonts()
    S = Config.SIZE

    # Barre haute — fond blanc semi-transparent
    ov = Image.new("RGBA", (S, 48), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(ov)
    for yy in range(48):
        alpha = int(220 * (1 - yy / 48))
        d2.line([(0, yy), (S, yy)], fill=(*P.UI_BG, alpha))
    img.paste(Image.alpha_composite(img.crop((0, 0, S, 48)).convert("RGBA"), ov), (0, 0))

    draw = ImageDraw.Draw(img)
    draw.text((12, 8), scene.titre[:38], fill=P.UI_TFG, font=F["med"])

    # Barre basse — fond blanc
    bh = int(S * .22)
    ov2 = Image.new("RGBA", (S, bh), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(ov2)
    for yy in range(bh):
        alpha = int(235 * (yy / bh) ** .4)
        d3.line([(0, yy), (S, yy)], fill=(*P.SONG_BG, alpha))
    img.paste(Image.alpha_composite(
        img.crop((0, S - bh, S, S)).convert("RGBA"), ov2), (0, S - bh))

    draw = ImageDraw.Draw(img)
    sl = song_line(song, scene.song_part)
    if sl:
        disp = sl[:40] + "…" if len(sl) > 42 else sl
        draw.text((12, S - bh + 8), f"♪  {disp}", fill=P.SONG_FG, font=F["small"])

    draw.line([(12, S - bh + 30), (S - 12, S - bh + 30)],
              fill=(200, 200, 230), width=1)

    dlg = scene.dialogue[:40] + "…" if len(scene.dialogue) > 42 else scene.dialogue
    draw.text((12, S - bh + 36), f"»  {dlg}", fill=P.UI_DFG, font=F["small"])

    # Barre de progression
    prog = f_in_scene / max(1, scene.duree)
    draw.rounded_rectangle([12, S - 14, S - 12, S - 4], radius=4,
                            fill=(220, 222, 240))
    fw = int((S - 24) * prog) + 12
    if fw > 22:
        draw.rounded_rectangle([12, S - 14, fw, S - 4], radius=4,
                                fill=P.UI_BAR)


def easing(t): return 3 * t ** 2 - 2 * t ** 3


def blend(f1, f2, t):
    return np.clip(f1 * (1 - t) + f2 * t, 0, 255).astype(np.uint8)


def render_scene(scene: Scene, genre: str, song: SongData,
                 gframe: int, theme_data: dict) -> List:
    frames = []
    for f in range(scene.duree):
        img = Image.new("RGBA", (Config.SIZE, Config.SIZE))
        draw = ImageDraw.Draw(img)
        draw_bg(draw, scene.decor, scene.sky_mood, gframe + f, theme_data)
        draw_char(draw, Config.SIZE // 2, int(Config.SIZE * .58),
                  scene.action, scene.emotion, gframe + f, genre)
        draw_ui(img, scene, f, song, genre)
        frames.append(cv2.cvtColor(
            np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR))
    return frames


def render_all(scenes: List[Scene], genre: str, song: SongData,
               theme_data: dict, progress_bar) -> List:
    all_frames = []
    gframe = 0
    EF = Config.EASE_FRAMES
    total = len(scenes)

    for i, scene in enumerate(scenes):
        pct = (i + 1) / total
        progress_bar.progress(
            pct,
            text=f"🎨 Rendu scène {i+1}/{total} — {scene.acte_label} : {scene.titre}"
        )
        sf = render_scene(scene, genre, song, gframe, theme_data)
        if all_frames and EF > 0:
            prev = all_frames[-EF:]
            nxt = sf[:EF]
            bl = [blend(prev[j], nxt[j], easing(j / EF))
                  for j in range(min(EF, len(prev), len(nxt)))]
            all_frames[-len(bl):] = bl
        all_frames.extend(sf)
        gframe += scene.duree

    progress_bar.progress(1.0, text="✅ Rendu terminé !")
    return all_frames


# ══════════════════════════════════════════════════════════
#  AUDIO
# ══════════════════════════════════════════════════════════
async def _edge_gen(text: str, voice: str, rate: str, pitch: str, out: str):
    communicate = edge_tts.Communicate(
        text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(out)


def gen_audio(char: Character, song: SongData, folder: str, status_placeholder) -> str:
    sections = [
        song.intro, "...", song.acte1, "...", song.acte2, "...",
        song.refrain1, "...", song.acte3, "...", song.acte4, "...",
        song.refrain2, "...", song.acte5, "...", song.acte6, "...",
        song.outro, "...", song.refrain2
    ]
    full_text = "  ".join(sections)
    voice = Config.VOICE_FILLE if char.genre == "fille" else Config.VOICE_GARCON
    vpath = os.path.join(folder, "voix.mp3")
    ok = False

    if _EDGE_TTS_OK:
        try:
            status_placeholder.info("🎙️ Génération voix neurale (edge-tts)...")
            asyncio.run(_edge_gen(
                full_text, voice, Config.VOICE_RATE, Config.VOICE_PITCH, vpath))
            ok = True
        except Exception as e:
            st.warning(f"edge-tts indisponible : {e} → Utilisation de gTTS")

    if not ok:
        status_placeholder.info("🎙️ Génération voix (gTTS)...")
        gTTS(text=full_text, lang="fr", slow=True).save(vpath)

    return vpath


def encode_video(frames: List, audio_path: str,
                 folder: str, prenom: str) -> str:
    silent  = os.path.join(folder, "_silent.mp4")
    final   = os.path.join(folder, f"ANIME_{prenom.upper()}.mp4")
    h, w    = frames[0].shape[:2]

    writer = cv2.VideoWriter(
        silent, cv2.VideoWriter_fourcc(*"mp4v"), Config.FPS, (w, h))
    for frame in frames:
        writer.write(frame)
    writer.release()

    subprocess.run([
        "ffmpeg", "-y",
        "-i", silent,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(Config.CRF),
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest", final
    ], capture_output=True, text=True)

    if os.path.exists(silent):
        os.remove(silent)
    return final


# ══════════════════════════════════════════════════════════
#  HELPERS UI
# ══════════════════════════════════════════════════════════
def stepper_html(current: int) -> str:
    labels = ["La bêtise", "Vérification", "Scénario", "Vidéo"]
    icons  = ["✏️", "🔍", "🎬", "🎉"]
    parts  = []
    for i in range(1, 5):
        if i < current:
            cls_dot = "sc-done"
            cls_txt = "sc-done"
            num_txt = "✓"
        elif i == current:
            cls_dot = "sc-active"
            cls_txt = "sc-active"
            num_txt = icons[i-1]
        else:
            cls_dot = ""
            cls_txt = ""
            num_txt = str(i)

        parts.append(f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
          <div class="step-circle {cls_dot}">{num_txt}</div>
          <div class="step-txt {cls_txt}">{labels[i-1]}</div>
        </div>""")

        if i < 4:
            done_cls = "sc-done" if i < current else ""
            parts.append(f'<div class="step-connector {done_cls}"></div>')

    return f'<div class="stepper-wrap">{"".join(parts)}</div>'


def card(content: str) -> None:
    st.markdown(f'<div class="anime-card">{content}</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  INTERFACE STREAMLIT PRINCIPALE
# ══════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="Studio Animé Éducatif",
        page_icon="🎬",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    apply_light_theme()

    # ── Session State ──
    for key, default in {
        "step": 1,
        "api_key": "",
        "betise": "",
        "validation": None,
        "scenario_data": None,
        "char": None,
        "song": None,
        "theme_key": "general",
        "show_api": False,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Héro ──
    st.markdown("""
    <div class="hero-banner">
        <h1>🎬 Studio Animé Éducatif</h1>
        <p>Transforme la bêtise de ton enfant en dessin animé personnalisé — éducatif et bienveillant ✨</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Stepper ──
    st.markdown(stepper_html(st.session_state.step), unsafe_allow_html=True)

    # ═══════════════════════════════════════
    #  ÉTAPE 1 — LA BÊTISE
    # ═══════════════════════════════════════
    if st.session_state.step == 1:
        with st.container():
            st.markdown('<div class="section-title">🔑 Clé API Groq</div>',
                        unsafe_allow_html=True)

            col_key, col_eye = st.columns([9, 1])
            with col_key:
                key_type = "text" if st.session_state.show_api else "password"
                api_key = st.text_input(
                    "Clé API",
                    value=st.session_state.api_key,
                    type=key_type,
                    placeholder="gsk_...",
                    label_visibility="collapsed"
                )
                st.session_state.api_key = api_key
            with col_eye:
                if st.button("👁" if not st.session_state.show_api else "🙈",
                             help="Afficher/Masquer"):
                    st.session_state.show_api = not st.session_state.show_api
                    st.rerun()

            st.markdown("""
            <div class="info-note">
            🔒 Obtiens ta clé <strong>gratuite</strong> sur
            <a href="https://console.groq.com" target="_blank" style="color:#1d4ed8;">
            console.groq.com</a> →
            <strong>API Keys → Create API Key</strong>. La clé n'est jamais sauvegardée.
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        st.markdown('<div class="section-title">✏️ Décris la bêtise de ton enfant</div>',
                    unsafe_allow_html=True)
        betise = st.text_area(
            "La bêtise",
            value=st.session_state.betise,
            placeholder="Ex : Mon fils Adam, 5 ans, touche les prises électriques avec ses doigts",
            height=100,
            label_visibility="collapsed"
        )
        st.session_state.betise = betise

        st.markdown('<div class="section-title" style="font-size:0.95rem;">💡 Exemples — clique pour utiliser</div>',
                    unsafe_allow_html=True)

        cols = st.columns(3)
        for idx, ex in enumerate(EXAMPLES):
            with cols[idx % 3]:
                if st.button(
                    f"{ex['icon']} {ex['label']}",
                    key=f"ex_{idx}",
                    use_container_width=True,
                    help=ex["text"]
                ):
                    st.session_state.betise = ex["text"]
                    st.session_state.theme_key = ex["theme"]
                    st.rerun()

        st.divider()

        if st.button("🔍 Analyser la bêtise avec l'IA",
                     type="primary", use_container_width=True):
            if not st.session_state.api_key.strip():
                st.error("⚠️ Entre ta clé API Groq dans le champ ci-dessus — c'est gratuit !")
            elif not st.session_state.betise.strip():
                st.error("⚠️ Décris la bêtise de ton enfant avant de continuer.")
            elif not _GROQ_OK:
                st.error("La bibliothèque `groq` n'est pas installée. Relance l'app.")
            else:
                with st.spinner("🤖 L'IA Groq analyse ta phrase…"):
                    try:
                        result = validate_with_ai(
                            st.session_state.betise,
                            st.session_state.api_key
                        )
                        st.session_state.validation = result
                        if result.get("theme") in THEMES:
                            st.session_state.theme_key = result["theme"]
                        st.session_state.step = 2
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("L'IA n'a pas renvoyé un JSON valide. Réessaie.")
                    except Exception as e:
                        st.error(f"Erreur API Groq : {e}")

    # ═══════════════════════════════════════
    #  ÉTAPE 2 — VALIDATION
    # ═══════════════════════════════════════
    elif st.session_state.step == 2:
        v = st.session_state.validation
        theme = THEMES.get(st.session_state.theme_key, THEMES["general"])

        if v and v.get("valide"):
            st.markdown(f"""
            <div class="val-ok">
                <p style="font-size:1.05rem;font-weight:800;color:#166534;margin:0 0 8px;">
                    ✅ Contenu validé — parfait pour les enfants !</p>
                <p style="font-size:0.88rem;color:#15803d;margin:0;">{v.get("message_parent","")}</p>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            # Infos personnage
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"""
                <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:14px;
                     padding:1.25rem;text-align:center;">
                    <div style="font-size:3rem;">{theme['emoji']}</div>
                    <div style="font-weight:800;font-size:1.1rem;color:#0f172a;margin-top:6px;">
                        {v.get("prenom","?")}
                    </div>
                    <div style="font-size:0.85rem;color:#64748b;">
                        {v.get("age","")} ans · {v.get("genre","")}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style="padding:0.5rem 0;">
                    <div style="margin-bottom:10px;">
                        <span style="font-size:0.78rem;font-weight:700;color:#64748b;
                              text-transform:uppercase;letter-spacing:.05em;">Danger détecté</span><br>
                        <span style="font-weight:800;color:#dc2626;font-size:1rem;">
                            ⚠️ {v.get("danger","")}</span>
                    </div>
                    <div>
                        <span style="font-size:0.78rem;font-weight:700;color:#64748b;
                              text-transform:uppercase;letter-spacing:.05em;">Thème visuel</span><br>
                        <span class="theme-chip">{theme['label']}</span>
                    </div>
                    <div style="margin-top:10px;">
                        <span style="font-size:0.78rem;font-weight:700;color:#64748b;
                              text-transform:uppercase;letter-spacing:.05em;">Décor</span><br>
                        <span style="font-size:0.85rem;color:#475569;">{theme['description']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()

            col_back, col_ok = st.columns([1, 2])
            with col_back:
                if st.button("← Modifier", use_container_width=True):
                    st.session_state.step = 1
                    st.rerun()
            with col_ok:
                if st.button("✅ Valider — Générer le scénario",
                             type="primary", use_container_width=True):
                    with st.spinner("🎵 Génération du scénario personnalisé…"):
                        try:
                            data = generate_scenario(
                                st.session_state.betise,
                                st.session_state.theme_key,
                                st.session_state.api_key
                            )
                            st.session_state.scenario_data = data
                            char, song = parse_scenario(data)
                            st.session_state.char = char
                            st.session_state.song = song
                            st.session_state.step = 3
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("L'IA n'a pas renvoyé un JSON valide. Réessaie.")
                        except Exception as e:
                            st.error(f"Erreur API Groq : {e}")

        else:
            # Contenu non valide
            st.markdown(f"""
            <div class="val-error">
                <p style="font-size:1.05rem;font-weight:800;color:#991b1b;margin:0 0 8px;">
                    ⚠️ Ce contenu n'est pas adapté</p>
                <p style="font-size:0.88rem;color:#b91c1c;margin:0;">
                    {v.get("raison","") if v else "Erreur inconnue."}</p>
            </div>
            """, unsafe_allow_html=True)

            suggestions = v.get("suggestions", []) if v else []
            if suggestions:
                st.markdown("#### 💡 L'IA te propose ces alternatives :")
                for s in suggestions:
                    if st.button(f"→ {s}", key=f"sug_{s[:20]}"):
                        st.session_state.betise = s
                        st.session_state.step = 1
                        st.rerun()

            if st.button("← Réécrire ma phrase", type="primary",
                         use_container_width=True):
                st.session_state.step = 1
                st.rerun()

    # ═══════════════════════════════════════
    #  ÉTAPE 3 — SCÉNARIO
    # ═══════════════════════════════════════
    elif st.session_state.step == 3:
        char = st.session_state.char
        song = st.session_state.song
        data = st.session_state.scenario_data
        theme = THEMES.get(st.session_state.theme_key, THEMES["general"])

        if not char or not song:
            st.error("Données manquantes. Recommence depuis l'étape 1.")
            if st.button("← Retour"):
                st.session_state.step = 1
                st.rerun()
            return

        # Personnage
        st.markdown(f"""
        <div class="anime-card">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:64px;height:64px;border-radius:50%;
                     background:linear-gradient(135deg,{theme['color_primary']},
                     #ec4899);display:flex;align-items:center;
                     justify-content:center;font-size:2rem;flex-shrink:0;">
                     {'👧' if char.genre == 'fille' else '👦'}</div>
                <div>
                    <div style="font-size:1.4rem;font-weight:800;color:#0f172a;">
                        {char.prenom}</div>
                    <div style="font-size:0.9rem;color:#64748b;">
                        {char.age} ans · {char.genre}</div>
                    <div style="margin-top:6px;">
                        <span style="background:#fef2f2;border:1px solid #fca5a5;
                              border-radius:99px;padding:3px 10px;font-size:0.78rem;
                              font-weight:700;color:#dc2626;">
                              ⚠️ {data.get('danger_court','')}</span>
                        <span class="theme-chip" style="margin-left:6px;">
                              {theme['label']}</span>
                    </div>
                </div>
            </div>
            <div style="margin-top:12px;padding:10px;background:#f8fafc;
                 border-radius:10px;border:1px solid #e2e8f0;">
                <span style="font-weight:700;font-size:0.82rem;color:#475569;">🎨 Décor : </span>
                <span style="font-size:0.88rem;color:#374151;">
                    {data.get('decor_principal',theme['description'])}</span>
                &nbsp;·&nbsp;
                <span style="font-size:0.82rem;color:{theme['color_primary']};font-weight:700;">
                    {data.get('ambiance_couleur','')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Chanson complète
        with st.expander("🎵 Voir la chanson complète générée", expanded=False):
            parts = [
                ("🎵 Introduction", song.intro),
                ("📖 Acte I — Vie normale", song.acte1),
                ("😮 Acte II — La tentation", song.acte2),
                ("🚨 Refrain 1 — Avertissement", song.refrain1),
                ("⚠️ Acte III — La bêtise", song.acte3),
                ("💥 Acte IV — Conséquence", song.acte4),
                ("💡 Refrain 2 — La leçon", song.refrain2),
                ("😢 Acte V — Il comprend", song.acte5),
                ("🤝 Acte VI — La promesse", song.acte6),
                ("🫵 Message final", song.outro),
            ]
            for label, texte in parts:
                st.markdown(f"""
                <div class="song-part">
                    <div class="song-part-label">{label}</div>
                    <div class="song-part-text">{texte}</div>
                </div>
                """, unsafe_allow_html=True)

        # Aperçu des scènes
        scenes_preview = [
            ("🏠", "Intro"),    ("🌳", "Acte I"),   ("😮", "Acte II"),
            ("🚨", "Refrain"),  ("⚠️", "Acte III"), ("💥", "Acte IV"),
            ("💡", "Refrain"),  ("😢", "Acte V"),   ("🤝", "Acte VI"),
            ("🎉", "Fin"),
        ]
        cols_s = st.columns(5)
        for i, (ic, nm) in enumerate(scenes_preview):
            with cols_s[i % 5]:
                st.markdown(f"""
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                     padding:10px 4px;text-align:center;margin-bottom:6px;">
                    <div style="font-size:1.4rem;">{ic}</div>
                    <div style="font-size:0.68rem;font-weight:700;color:#64748b;margin-top:4px;">
                        {nm}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        col_b, col_g = st.columns([1, 2])
        with col_b:
            if st.button("← Modifier", use_container_width=True):
                st.session_state.step = 1
                st.rerun()
        with col_g:
            if st.button("🎬 Lancer la génération vidéo",
                         type="primary", use_container_width=True):
                st.session_state.step = 4
                st.rerun()

    # ═══════════════════════════════════════
    #  ÉTAPE 4 — GÉNÉRATION VIDÉO
    # ═══════════════════════════════════════
    elif st.session_state.step == 4:
        char  = st.session_state.char
        song  = st.session_state.song
        theme_data = THEMES.get(st.session_state.theme_key, THEMES["general"])

        if not char or not song:
            st.error("Données manquantes.")
            if st.button("← Retour"):
                st.session_state.step = 1
                st.rerun()
            return

        st.markdown(f"""
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:14px;
             padding:1rem;margin-bottom:1rem;display:flex;gap:12px;align-items:center;">
            <div style="font-size:2rem;">{'👧' if char.genre=='fille' else '👦'}</div>
            <div>
                <div style="font-weight:800;font-size:1.1rem;color:#0f172a;">
                    {char.prenom} · {char.age} ans</div>
                <div style="font-size:0.85rem;color:#64748b;">
                    🎵 {song.titre}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.status("⚙️ Génération en cours...", expanded=True) as status:

            # — Rendu vidéo —
            st.write("🎨 Rendu vidéo frame par frame...")
            scenes     = build_scenes(char, song, st.session_state.theme_key)
            prog_bar   = st.progress(0, text="Démarrage du rendu…")
            frames     = render_all(scenes, char.genre, song, theme_data, prog_bar)

            # — Audio —
            st.write("🎙️ Génération de la voix...")
            audio_status = st.empty()

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = gen_audio(char, song, tmpdir, audio_status)
                audio_status.empty()

                # — Encodage —
                st.write("⚙️ Encodage MP4 final...")
                final_path = encode_video(
                    frames, audio_path, tmpdir, char.prenom)

                if not os.path.exists(final_path):
                    st.error("❌ Erreur encodage. Vérifie que ffmpeg est installé.")
                    st.stop()

                with open(final_path, "rb") as fv:
                    video_bytes = fv.read()

            status.update(label="✅ Vidéo générée avec succès !",
                          state="complete", expanded=False)

        # — Résultat —
        st.success(f"🎉 La vidéo de **{char.prenom}** est prête !")
        st.video(video_bytes)

        st.download_button(
            label=f"💾 Télécharger la vidéo MP4 — {char.prenom}",
            data=video_bytes,
            file_name=f"anime_{char.prenom.lower()}_{st.session_state.scenario_data.get('danger_court','').replace(' ','_')}.mp4",
            mime="video/mp4",
            use_container_width=True,
            type="primary"
        )

        st.divider()
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            if st.button("🔄 Créer une nouvelle vidéo",
                         use_container_width=True, type="primary"):
                for key in ["step","betise","validation","scenario_data",
                            "char","song","theme_key"]:
                    st.session_state[key] = 1 if key == "step" else \
                        "general" if key == "theme_key" else \
                        "" if key == "betise" else None
                st.rerun()
        with col_n2:
            st.info("💡 Partage cette vidéo avec ton enfant pour apprendre en s'amusant !")

    # ── Footer ──
    st.markdown("---")
    st.markdown(
        "<p style='text-align:center;font-size:0.78rem;color:#94a3b8;'>"
        "Studio Animé Éducatif · Propulsé par Groq AI (100% gratuit) · "
        "Pour les enfants de 3 à 8 ans · Contenu bienveillant et éducatif</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
