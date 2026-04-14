"""
╔══════════════════════════════════════════════════════════════════╗
║   STUDIO ANIMÉ ÉDUCATIF — Version 3 Professionnelle             ║
║   Streamlit + Groq API (GRATUIT)                                 ║
║   Clé API sidebar · Validation inline · 3 étapes épurées        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import subprocess, sys, os, re, math, asyncio, json, tempfile
from dataclasses import dataclass
from typing import List
import warnings
warnings.filterwarnings("ignore")

@st.cache_resource
def install_deps():
    for pkg in ["groq","edge-tts","gtts","pydub","opencv-python-headless","pillow","numpy"]:
        subprocess.run([sys.executable,"-m","pip","install","-q",pkg],capture_output=True)
    return True
install_deps()

import cv2, numpy as np
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

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
class Cfg:
    FPS=24; SIZE=512; CRF=23; EF=6
    FONT_DIR="/usr/share/fonts/truetype/dejavu/"
    FONT_B=FONT_DIR+"DejaVuSans-Bold.ttf"
    FONT_R=FONT_DIR+"DejaVuSans.ttf"
    VF="fr-FR-DeniseNeural"; VG="fr-FR-HenriNeural"
    VRATE="-20%"; VPITCH="+5Hz"
    MODEL="llama-3.1-8b-instant"

# ─────────────────────────────────────────
#  DATACLASSES
# ─────────────────────────────────────────
@dataclass
class Character:
    prenom:str; age:int; genre:str

@dataclass
class SongData:
    titre:str; intro:str; acte1:str; acte2:str
    refrain1:str; acte3:str; acte4:str; refrain2:str
    acte5:str; acte6:str; outro:str

@dataclass
class Scene:
    titre:str; acte_label:str; decor:str; action:str
    emotion:str; dialogue:str; duree:int
    sky_mood:str="day"; song_part:str=""
    image_prompt:str=""
    bg_img:Image.Image=None

# ─────────────────────────────────────────
#  THÈMES VISUELS
# ─────────────────────────────────────────
THEMES = {
    "electric":{"label":"⚡ Électricité","emoji":"⚡","color":"#6366f1",
        "sky_n":((100,140,255),(180,210,255)),"sky_d":((180,60,40),(120,40,30)),"sky_g":((255,160,40),(255,200,100)),
        "gnd":(60,160,60),"gnds":(40,120,40),"fx":(80,200,255),"wall":(240,240,255),
        "desc":"Maison moderne, prises électriques, éclairs bleus"},
    "kitchen":{"label":"🍳 Cuisine","emoji":"🍳","color":"#f97316",
        "sky_n":((255,220,150),(255,240,180)),"sky_d":((200,80,20),(140,50,10)),"sky_g":((255,180,60),(255,220,100)),
        "gnd":(100,70,40),"gnds":(70,50,25),"fx":(255,120,0),"wall":(255,230,200),
        "desc":"Grande cuisine familiale, couteaux, flammes orange"},
    "meds":{"label":"💊 Médicaments","emoji":"💊","color":"#a855f7",
        "sky_n":((200,180,255),(230,220,255)),"sky_d":((120,40,160),(80,20,120)),"sky_g":((220,180,255),(240,210,255)),
        "gnd":(80,160,80),"gnds":(55,120,55),"fx":(200,100,255),"wall":(240,230,255),
        "desc":"Salle de bain, armoire à pharmacie, lumière violette"},
    "pool":{"label":"🏊 Piscine","emoji":"🏊","color":"#0ea5e9",
        "sky_n":((60,160,255),(150,210,255)),"sky_d":((20,60,140),(10,40,100)),"sky_g":((255,200,80),(255,230,130)),
        "gnd":(0,120,200),"gnds":(0,90,160),"fx":(100,220,255),"wall":(200,240,255),
        "desc":"Piscine extérieure, eau bleue, carrelage blanc"},
    "road":{"label":"🚦 Route","emoji":"🚦","color":"#64748b",
        "sky_n":((140,180,230),(190,215,245)),"sky_d":((160,80,40),(120,60,30)),"sky_g":((255,180,60),(255,210,110)),
        "gnd":(80,80,80),"gnds":(55,55,55),"fx":(255,255,0),"wall":(200,200,210),
        "desc":"Rue de ville, passage piéton, feux de signalisation"},
    "fire":{"label":"🔥 Feu / Gaz","emoji":"🔥","color":"#ef4444",
        "sky_n":((255,180,100),(255,210,150)),"sky_d":((200,50,0),(140,30,0)),"sky_g":((255,160,40),(255,200,90)),
        "gnd":(70,160,70),"gnds":(50,120,50),"fx":(255,80,0),"wall":(255,220,195),
        "desc":"Cuisine avec gaz, flammes rouges dramatiques"},
    "general":{"label":"🌟 Général","emoji":"🌟","color":"#6366f1",
        "sky_n":((100,160,255),(200,230,255)),"sky_d":((220,80,50),(150,60,40)),"sky_g":((255,180,60),(255,220,120)),
        "gnd":(70,175,70),"gnds":(50,130,50),"fx":(255,200,0),"wall":(255,235,210),
        "desc":"Environnement général coloré et adapté"},
}

EXAMPLES = [
    {"icon":"⚡","label":"Prises électriques","text":"Mon fils Adam, 5 ans, touche les prises électriques","theme":"electric"},
    {"icon":"🔪","label":"Couteaux","text":"Mon fils Youssef, 7 ans, joue avec les couteaux de cuisine","theme":"kitchen"},
    {"icon":"💊","label":"Médicaments","text":"Ma fille Inès, 6 ans, mange des médicaments","theme":"meds"},
    {"icon":"🏊","label":"Piscine","text":"Ma fille Lina, 4 ans, s'approche seule du bord de la piscine","theme":"pool"},
    {"icon":"🚗","label":"Traverser la rue","text":"Mon fils Rayan, 6 ans, traverse la rue sans regarder","theme":"road"},
    {"icon":"🔥","label":"Feu / Gaz","text":"Ma fille Sara, 5 ans, allume les boutons du gaz","theme":"fire"},
]

# ─────────────────────────────────────────
#  PROMPTS
# ─────────────────────────────────────────
VAL_PROMPT="""Tu es un modérateur d'application éducative pour enfants de 3 à 8 ans.
Analyse cette phrase parentale et réponds UNIQUEMENT en JSON valide sans markdown :
{
  "valide": true,
  "raison": "courte explication",
  "prenom": "prénom ou null",
  "age": 5,
  "genre": "garçon ou fille",
  "danger": "type danger 3 mots",
  "theme": "electric|kitchen|meds|pool|road|fire|general",
  "comprehension": "En simple : ce que l'enfant fait exactement (1 phrase bienveillante)",
  "conseils": ["conseil court 1","conseil court 2","conseil court 3"],
  "message_parent": "message encourageant 1 phrase",
  "suggestions": ["phrase alternative 1","phrase alternative 2"]
}
Phrase : {betise}"""

SCN_PROMPT="""Tu es auteur de livres éducatifs pour enfants 3-8 ans. Génère une chanson narrative rimée.
Décor : {theme_desc}. Réponds UNIQUEMENT JSON valide sans markdown :
{{"prenom":"{prenom}","age":{age},"genre":"{genre}","danger_court":"3 mots max",
"decor_principal":"8 mots max","ambiance_couleur":"couleur dominante",
"scenes_narration":[
  "Scène 1 Introduction : phrase courte qui décrit ce qui se passe (max 8 mots)",
  "Scène 2 Vie normale : phrase courte",
  "Scène 3 Belle journée : phrase courte",
  "Scène 4 Découverte : phrase courte",
  "Scène 5 Une idée : phrase courte",
  "Scène 6 Attention danger : phrase courte",
  "Scène 7 Non non non : phrase courte",
  "Scène 8 La bêtise : phrase courte",
  "Scène 9 Conséquences : phrase courte",
  "Scène 10 Au secours : phrase courte",
  "Scène 11 La leçon : phrase courte",
  "Scène 12 Comprend : phrase courte",
  "Scène 13 La promesse : phrase courte",
  "Scène 14 Et toi : phrase courte",
  "Scène 15 Au revoir : phrase courte"
],
"image_prompts":[
  "Describe scene 1 background in English (e.g. colorful living room)",
  "Describe scene 2 background in English based on story",
  "Describe scene 3 background in English based on story",
  "Describe scene 4 background in English based on story",
  "Describe scene 5 background in English based on story",
  "Describe scene 6 background in English based on story",
  "Describe scene 7 background in English based on story",
  "Describe scene 8 background in English based on story",
  "Describe scene 9 background in English based on story",
  "Describe scene 10 background in English based on story",
  "Describe scene 11 background in English based on story",
  "Describe scene 12 background in English based on story",
  "Describe scene 13 background in English based on story",
  "Describe scene 14 background in English based on story",
  "Describe scene 15 background in English based on story"
],
"song":{{"titre":"La Chanson de {prenom} et [danger]",
"intro":"2-3 phrases d'accroche rimées","acte1":"vie normale 3-4 phrases rimées",
"acte2":"découverte objet dangereux 3-4 phrases rimées",
"refrain1":"avertissement NON NON NON 3-4 phrases rimées",
"acte3":"commet la bêtise 2-3 phrases dramatiques",
"acte4":"conséquence terrible 3-4 phrases rimées",
"refrain2":"leçon et bonne solution 3-4 phrases rimées",
"acte5":"comprend et pleure 3-4 phrases émouvantes",
"acte6":"promesse solennelle 3-4 phrases rimées",
"outro":"message direct à l'enfant spectateur 2-3 phrases"}}}}
Phrase : {betise}"""

# ─────────────────────────────────────────
#  IA — GROQ
# ─────────────────────────────────────────
def _extract_json(raw: str) -> str:
    """Extrait le JSON même si du texte entoure le bloc."""
    # 1. Retirer les blocs markdown ```json ... ```
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    raw = re.sub(r"```", "", raw).strip()
    # 2. Trouver le premier { et le dernier }
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end+1]
    return raw

def _call(api_key: str, prompt: str, max_tok: int = 800) -> dict:
    """Appelle Groq et retourne un dict JSON parsé."""
    c = _GroqClient(api_key=api_key)
    m = c.chat.completions.create(
        model=Cfg.MODEL,
        max_tokens=max_tok,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system",
             "content": "Tu es un assistant qui répond UNIQUEMENT en JSON valide."},
            {"role": "user", "content": prompt}
        ]
    )
    raw = m.choices[0].message.content.strip()
    cleaned = _extract_json(raw)
    return json.loads(cleaned)

def validate_ai(betise: str, api_key: str) -> dict:
    return _call(api_key, VAL_PROMPT.replace("{betise}", betise), 900)

# ─────────────────────────────────────────
#  CHAT PROMPT — conversation libre + détection scénario
# ─────────────────────────────────────────
CHAT_PROMPT = """
Tu es un assistant pédagogique chaleureux, bienveillant et professionnel, spécialisé dans
l'éducation et la sécurité des enfants de 3 à 8 ans. Tu parles UNIQUEMENT français.

Règle 1 — CONVERSATION NORMALE : Si le parent dit bonjour, pose une question générale,
parle de la météo, demande une définition, etc. → réponds naturellement et chaleureusement.

Règle 2 — MODE SCÉNARIO : Si le parent décrit un comportement DANGEREUX ou INTERDIT d'un
enfant (en mentionnant un prénom et un âge), -> active le mode scénario éducatif.

Réponds UNIQUEMENT en JSON valide sans markdown :

Pour conversation normale :
{{"type":"general","response":"ta réponse naturelle et amicale"}}

Pour scénario éducatif :
{{"type":"scenario","response":"réponse naturelle qui confirme la compréhension",
"valide":true,"raison":"","prenom":"prénom","age":5,"genre":"garçon ou fille",
"danger":"3 mots","theme":"electric|kitchen|meds|pool|road|fire|general",
"comprehension":"ce que l'enfant fait (1 phrase bienveillante)",
"conseils":["conseil 1","conseil 2","conseil 3"],
"message_parent":"message encourageant",
"suggestions":["phrase enrichie 1","phrase enrichie 2"]}}

Pour message hors sujet ou inapproprié :
{{"type":"invalid","response":"explication polie pourquoi tu ne peux pas aider",
"suggestions":["exemple de message adapté 1","exemple 2"]}}

Message du parent : {message}
"""

def chat_ai(message: str, api_key: str) -> dict:
    """Analyse le message et retourne type general/scenario/invalid + réponse."""
    prompt = CHAT_PROMPT.replace("{message}", message)
    return _call(api_key, prompt, 1200)

def scenario_ai(betise: str, val: dict, api_key: str) -> dict:
    theme_val = val.get("theme") or "general"
    t = THEMES.get(theme_val, THEMES["general"])
    p = SCN_PROMPT.replace("{betise}", betise).replace("{theme_desc}", t["desc"])
    prenom = val.get("prenom") or "l'enfant"
    age = val.get("age") or 5
    genre = val.get("genre") or "garçon"
    p = p.replace("{prenom}", str(prenom))
    p = p.replace("{age}", str(age))
    p = p.replace("{genre}", str(genre))
    return _call(api_key, p, 3000)

def parse_scenario(d: dict) -> tuple:
    prenom = d.get("prenom") or ""
    age = d.get("age") or 5
    genre = d.get("genre") or "garçon"
    char = Character(prenom=str(prenom), age=int(age), genre=str(genre))
    s = d["song"]
    song = SongData(titre=s.get("titre",""), intro=s.get("intro",""), acte1=s.get("acte1",""),
        acte2=s.get("acte2",""), refrain1=s.get("refrain1",""), acte3=s.get("acte3",""),
        acte4=s.get("acte4",""), refrain2=s.get("refrain2",""), acte5=s.get("acte5",""),
        acte6=s.get("acte6",""), outro=s.get("outro",""))
    # Récupère les 15 narrations générées par l'IA
    raw_narr = d.get("scenes_narration", [])
    # Nettoie les narrations (retire le préfixe "Scène X : " si présent)
    narrations = []
    for n in raw_narr:
        txt = str(n)
        if ":" in txt:
            txt = txt.split(":", 1)[-1].strip()
        narrations.append(txt)
    # Complète si l'IA donne moins de 15 narrations
    defaults = [
        f"{char.prenom} est prêt pour l'aventure !",
        f"{char.prenom} joue joyeusement.",
        "Une belle journée commence.",
        "Quelque chose attire son attention...",
        "Une idée dangereuse germe...",
        "ATTENTION ! C'est dangereux !",
        "Non non non ! N'fais pas ça !",
        f"{char.prenom} n'écoute pas...",
        "Oh non ! Les conséquences arrivent !",
        "Au secours ! À l'aide !",
        "Voilà ce qu'il faut faire.",
        f"{char.prenom} comprend sa bêtise.",
        "Une promesse solennelle est faite.",
        "Et toi, tu ferais comment ?",
        "Bravo d'avoir appris avec nous !",
    ]
    while len(narrations) < 15:
        narrations.append(defaults[len(narrations)])
        
    img_prompts = d.get("image_prompts", [])
    while len(img_prompts) < 15:
        img_prompts.append("beautiful landscape, children book illustration style, detailed scene")
        
    return char, song, narrations[:15], img_prompts[:15]

# ─────────────────────────────────────────
#  LABELS DE LIEU (affichés dans la vidéo)
# ─────────────────────────────────────────
DECOR_LABELS = {
    "maison":  "🏠 Dans la maison",
    "parc":    "🌳 Dans le parc",
    "danger":  "⚠️ Zone de danger",
    "cuisine": "🍳 Dans la cuisine",
    "rue":     "🚦 Dans la rue",
    "piscine": "🏊 Bord de piscine",
    "bain":    "🛁 Salle de bain",
}

def build_scenes(char: Character, song: SongData, tk: str, narrations: list, img_prompts: list) -> List[Scene]:
    p = char.prenom; f = Cfg.FPS
    dm = {"electric": ["maison","parc","maison","maison","maison","danger"]+["parc"]*9,
          "kitchen":  ["maison","parc","maison","maison","maison","danger"]+["parc"]*9,
          "pool":     ["parc"]*3+["danger"]*3+["parc"]*9,
          "road":     ["parc"]*3+["danger"]*3+["parc"]*9}
    d = dm.get(tk, ["parc"]*15)
    # Utilise les narrations IA comme dialogue de chaque scène
    n = narrations  # alias court
    ip = img_prompts
    return [
        Scene("Introduction",    "Intro",    d[0],  "saute_joie",       "heureux",   n[0],  f*5,  "day",    "intro", ip[0]),
        Scene(f"La vie de {p}", "Acte I",   d[1],  "court_vite",       "heureux",   n[1],  f*5,  "day",    "acte1", ip[1]),
        Scene("Belle journée",  "Acte I",   d[2],  "marche_content",   "heureux",   n[2],  f*4,  "golden", "acte1", ip[2]),
        Scene("Qu'est-ce?",     "Acte II",  d[3],  "decouvre_surpris", "curieux",   n[3],  f*5,  "golden", "acte2", ip[3]),
        Scene("Une idée...",    "Acte II",  d[4],  "hesite_balance",   "penseur",   n[4],  f*4,  "golden", "acte2", ip[4]),
        Scene("⚠️ ATTENTION!",  "Refrain",  d[5],  "appelle_gestes",   "effraye",   n[5],  f*5,  "day",    "refrain1", ip[5]),
        Scene("NON NON NON!",   "Refrain",  d[6],  "saute_peur",       "effraye",   n[6],  f*4,  "day",    "refrain1", ip[6]),
        Scene("La bêtise!",     "Acte III", d[7],  "fait_betise_saute","curieux",   n[7],  f*6,  "dusk",   "acte3", ip[7]),
        Scene("Conséquences!",  "Acte IV",  d[8],  "court_panique",    "effraye",   n[8],  f*6,  "dusk",   "acte4", ip[8]),
        Scene("AU SECOURS!",    "Acte IV",  d[9],  "appelle_gestes",   "effraye",   n[9],  f*5,  "dusk",   "acte4", ip[9]),
        Scene("La leçon",       "Refrain",  d[10], "ecoute_hoche",     "desole",    n[10], f*5,  "day",    "refrain2", ip[10]),
        Scene(f"{p} comprend",  "Acte V",   d[11], "pleure_assise",    "triste",    n[11], f*6,  "day",    "acte5", ip[11]),
        Scene("La promesse",    "Acte VI",  d[12], "saute_promesse",   "determine", n[12], f*5,  "day",    "acte6", ip[12]),
        Scene("Et toi?",        "Outro",    d[13], "pointe_enfant",    "heureux",   n[13], f*5,  "day",    "outro", ip[13]),
        Scene("À bientôt!",     "Outro",    d[14], "salue_saute",      "fier",      n[14], f*4,  "day",    "outro", ip[14]),
    ]

# ─────────────────────────────────────────
#  PALETTE
# ─────────────────────────────────────────
class P:
    SKIN=(255,232,205);CHEEK=(255,175,165);HAIR_B=(55,38,18);HAIR_G=(195,135,70)
    SHIRT_B=(70,130,255);SHIRT_G=(255,120,175);PANTS=(45,85,195);SHOE=(175,48,48)
    EYE_B=(80,160,255);EYE_G=(255,100,195);WHITE=(255,255,255);OUTLINE=(30,20,10)
    SUN=(255,245,100);TEAR=(90,195,255);FLAME_C=(255,230,80)
    ROOF=(185,80,60);DOOR=(110,65,35);WINDOW=(180,220,255)
    TREE_T=(85,52,28);TREE_L=(60,185,60)
    UI_BG=(245,247,252);UI_TFG=(30,30,80);UI_DFG=(60,60,140)
    SONG_BG=(245,245,255);SONG_FG=(80,60,180);UI_BAR=(99,102,241)

def lerp(a,b,t):return a+(b-a)*t
def lc(c1,c2,t):return tuple(int(lerp(a,b,t))for a,b in zip(c1,c2))
def grad(draw,x0,y0,x1,y1,tc,bc):
    for y in range(y0,y1):
        t=(y-y0)/max(1,y1-y0); draw.line([(x0,y),(x1,y)],fill=lc(tc,bc,t))

def get_sky(td,mood):
    if mood=="dusk": return td["sky_d"]
    if mood=="golden": return td["sky_g"]
    return td["sky_n"]

def draw_bg(draw,decor,mood,frame,td):
    S=Cfg.SIZE; tc,bc=get_sky(td,mood)
    grad(draw,0,0,S,int(S*.64),tc,bc)
    if mood!="dusk":
        sx,sy=int(S*.85),int(S*.09)
        draw.ellipse([sx-22,sy-22,sx+22,sy+22],fill=P.SUN)
        for ang in range(0,360,45):
            rx=sx+int(30*math.cos(math.radians(ang+frame*.3)))
            ry=sy+int(30*math.sin(math.radians(ang+frame*.3)))
            draw.line([(sx,sy),(rx,ry)],fill=P.SUN,width=2)
    gnd=td["gnds"]if mood=="dusk"else td["gnd"]
    draw.rectangle([0,int(S*.64),S,S],fill=gnd)
    if mood!="dusk":
        for i in range(4):
            cx2=(50+i*int(S/4)+int(3*math.sin(frame*.015+i*1.2)))%S
            cy2=int(S*.12)+i%2*int(S*.06)
            for dx in[-16,0,16]:
                draw.ellipse([cx2+dx-14,cy2-12,cx2+dx+14,cy2+12],fill=P.WHITE)
    tx,ty=int(S*.83),int(S*.64)
    draw.rectangle([tx-8,ty-int(S*.22),tx+8,ty],fill=P.TREE_T)
    draw.ellipse([tx-int(S*.09),ty-int(S*.32),tx+int(S*.09),ty-int(S*.16)],fill=P.TREE_L)
    if decor in("maison","danger"):
        wc=td.get("wall",P.WHITE); mx,my=28,int(S*.62); mw,mh=int(S*.30),int(S*.22)
        draw.rectangle([mx,my-mh,mx+mw,my],fill=wc,outline=P.OUTLINE,width=2)
        draw.polygon([mx-10,my-mh,mx+mw//2,my-mh-int(S*.10),mx+mw+10,my-mh],fill=P.ROOF,outline=P.OUTLINE,width=2)
        draw.rectangle([mx+mw//2-15,my-int(S*.10),mx+mw//2+15,my],fill=P.DOOR,outline=P.OUTLINE,width=2)
        wl=(255,255,180)if mood=="dusk"else P.WINDOW
        for wx2 in[mx+8,mx+mw-38]:
            draw.rectangle([wx2,my-int(S*.17),wx2+30,my-int(S*.10)],fill=wl,outline=P.OUTLINE,width=2)
        fx=td["fx"]
        if mood=="dusk":
            for fi in range(5):
                fh=28+int(16*math.sin(frame*.22+fi*.8)); fx2=mx+10+fi*int(mw/5)
                draw.ellipse([fx2-8,my-mh-fh,fx2+8,my-mh],fill=fx)
                draw.ellipse([fx2-4,my-mh-fh-8,fx2+4,my-mh-6],fill=P.FLAME_C)
    if decor=="danger":
        fx=td["fx"]
        for i in range(6):
            angle=math.radians(i*60+frame*3)
            ex=int(S*.5)+int(80*math.cos(angle)); ey=int(S*.45)+int(50*math.sin(angle))
            r=6+int(4*math.sin(frame*.18+i))
            draw.ellipse([ex-r,ey-r,ex+r,ey+r],fill=fx)

def anim_off(action,frame):
    if action in("saute_joie","saute_promesse","salue_saute","fait_betise_saute"):
        return 0,-abs(int(30*math.sin(frame*.16)))
    if action=="saute_peur": return int(4*math.sin(frame*.45)),-abs(int(18*math.sin(frame*.32)))
    if action in("court_vite","marche_content","court_panique"):
        return int(5*math.sin(frame*.12)),int(5*math.sin(frame*.22))
    if action=="pleure_assise": return 0,int(Cfg.SIZE*.04)
    return 0,int(3*math.sin(frame*.07))

def draw_char(draw,cx,cy,action,emotion,frame,genre):
    S=Cfg.SIZE; dx,dy=anim_off(action,frame); x,y=cx+dx,cy+dy
    shirt=P.SHIRT_G if genre=="fille" else P.SHIRT_B
    hair=P.HAIR_G if genre=="fille" else P.HAIR_B
    eye_c=P.EYE_G if genre=="fille" else P.EYE_B
    draw.ellipse([cx-int(S*.06),cy+int(S*.015),cx+int(S*.06),cy+int(S*.03)],fill=(30,30,30))
    if emotion=="triste": shirt=lc(shirt,(130,130,160),.4)
    elif emotion=="effraye": shirt=lc(shirt,(180,180,190),.35)
    draw.ellipse([x-int(S*.05),y-int(S*.04),x+int(S*.05),y+int(S*.075)],fill=shirt,outline=P.OUTLINE,width=2)
    if action=="pleure_assise":
        draw.ellipse([x-int(S*.06),y+int(S*.07),x+int(S*.01),y+int(S*.13)],fill=P.PANTS,outline=P.OUTLINE,width=2)
        draw.ellipse([x+int(S*.01),y+int(S*.07),x+int(S*.06),y+int(S*.13)],fill=P.PANTS,outline=P.OUTLINE,width=2)
    else:
        sw=int(20*math.sin(frame*.2))if action in("court_vite","marche_content","court_panique")else 3
        draw.line([x-int(S*.02),y+int(S*.065),x-int(S*.03)-sw,y+int(S*.12)],fill=P.PANTS,width=int(S*.022))
        draw.line([x+int(S*.02),y+int(S*.065),x+int(S*.03)+sw,y+int(S*.12)],fill=P.PANTS,width=int(S*.022))
        draw.ellipse([x-int(S*.05)-sw,y+int(S*.11),x-int(S*.01)-sw,y+int(S*.135)],fill=P.SHOE,outline=P.OUTLINE,width=2)
        draw.ellipse([x+int(S*.01)+sw,y+int(S*.11),x+int(S*.05)+sw,y+int(S*.135)],fill=P.SHOE,outline=P.OUTLINE,width=2)
    sk=P.SKIN
    def arm(x1,y1,x2,y2):
        draw.line([x1,y1,x2,y2],fill=sk,width=int(S*.018))
        draw.ellipse([x2-5,y2-5,x2+5,y2+5],fill=sk,outline=P.OUTLINE,width=1)
    sw2=int(22*math.sin(frame*.18))
    if action=="saute_joie":
        arm(x-int(S*.046),y-int(S*.008),x-int(S*.084),y-int(S*.078))
        arm(x+int(S*.046),y-int(S*.008),x+int(S*.084),y-int(S*.078))
    elif action in("court_vite","marche_content","court_panique"):
        arm(x-int(S*.046),y,x-int(S*.07)+sw2,y+int(S*.022))
        arm(x+int(S*.046),y,x+int(S*.07)-sw2,y+int(S*.022))
    elif action=="appelle_gestes":
        gh=int(30*math.sin(frame*.16))
        arm(x-int(S*.046),y,x-int(S*.09),y-int(S*.062)-gh)
        arm(x+int(S*.046),y,x+int(S*.09),y-int(S*.062)+gh)
    elif action=="saute_peur":
        t2=int(6*math.sin(frame*.45))
        arm(x-int(S*.046),y+t2,x-int(S*.075),y-int(S*.05)+t2)
        arm(x+int(S*.046),y-t2,x+int(S*.075),y-int(S*.05)-t2)
    elif action=="pointe_enfant":
        arm(x-int(S*.046),y,x-int(S*.06),y+int(S*.022))
        draw.line([x+int(S*.046),y,x+int(S*.1),y-int(S*.02)],fill=sk,width=int(S*.018))
        draw.ellipse([x+int(S*.094),y-int(S*.035),x+int(S*.116),y-int(S*.013)],fill=sk,outline=P.OUTLINE,width=1)
    elif action in("saute_promesse","salue_saute"):
        arm(x-int(S*.046),y,x-int(S*.06),y+int(S*.025))
        arm(x+int(S*.046),y,x+int(S*.08),y-int(S*.086))
    elif action=="fait_betise_saute":
        arm(x-int(S*.046),y,x-int(S*.07),y-int(S*.03))
        arm(x+int(S*.046),y,x+int(S*.086),y-int(S*.04))
    elif action=="pleure_assise":
        arm(x-int(S*.046),y+int(S*.034),x-int(S*.025),y+int(S*.066))
        arm(x+int(S*.046),y+int(S*.034),x+int(S*.025),y+int(S*.066))
    elif action=="decouvre_surpris":
        arm(x+int(S*.046),y,x+int(S*.084),y+int(S*.005))
        arm(x-int(S*.046),y,x-int(S*.06),y+int(S*.025))
    else:
        arm(x-int(S*.046),y,x-int(S*.062),y+int(S*.022))
        arm(x+int(S*.046),y,x+int(S*.062),y+int(S*.022))
    hy=y-int(S*.13)
    draw.ellipse([x-int(S*.066),hy,x+int(S*.066),hy+int(S*.136)],fill=P.SKIN,outline=P.OUTLINE,width=2)
    draw.arc([x-int(S*.064),hy,x+int(S*.064),hy+int(S*.07)],180,0,fill=hair,width=10)
    if genre=="fille":
        draw.rectangle([x-int(S*.07),hy+int(S*.012),x-int(S*.042),hy+int(S*.094)],fill=hair)
        draw.rectangle([x+int(S*.042),hy+int(S*.012),x+int(S*.07),hy+int(S*.094)],fill=hair)
    ey=hy+int(S*.054); ew,eh=14,12
    if emotion in("surpris","effraye"): eh=16
    elif emotion in("heureux","fier"): eh=10
    cligne=(frame%75)<3
    for side in(-1,1):
        ox=x+side*int(S*.034)
        if cligne:
            draw.arc([ox-ew,ey-3,ox+ew,ey+5],0,180,fill=P.OUTLINE,width=2)
        else:
            draw.ellipse([ox-ew,ey-eh,ox+ew,ey+eh],fill=P.WHITE,outline=P.OUTLINE,width=2)
            draw.ellipse([ox-6,ey-5,ox+6,ey+5],fill=eye_c)
            draw.ellipse([ox-4,ey-3,ox+4,ey+3],fill=(8,8,18))
            draw.ellipse([ox-10,ey-8,ox-3,ey-2],fill=P.WHITE)
    draw.ellipse([x-int(S*.076),ey+5,x-int(S*.044),ey+20],fill=P.CHEEK)
    draw.ellipse([x+int(S*.044),ey+5,x+int(S*.076),ey+20],fill=P.CHEEK)
    my2=hy+int(S*.096)
    if emotion in("heureux","fier","determine"): draw.arc([x-10,my2-5,x+10,my2+8],0,180,fill=(185,65,65),width=3)
    elif emotion in("triste","desole"): draw.arc([x-10,my2+5,x+10,my2+14],180,0,fill=(178,65,65),width=3)
    elif emotion in("surpris","effraye"): draw.ellipse([x-9,my2-2,x+9,my2+14],fill=(135,48,48))
    else: draw.line([x-7,my2+6,x+7,my2+6],fill=(168,68,68),width=2)
    if emotion=="triste":
        for s2 in(-1,1):
            lx=x+s2*int(S*.056); ly=ey+int(S*.025)+int(5*math.sin(frame*.22+s2))
            draw.polygon([lx-4,ly,lx+4,ly,lx,ly+14],fill=P.TEAR)
    if action in("court_vite","court_panique"):
        for li in range(4):
            lx2=x-int(S*.12)-li*10; ly2=y+li*6
            draw.line([lx2,ly2,lx2+int(S*.044),ly2],fill=(160,165,190),width=2)

_FONTS=None
def get_fonts():
    global _FONTS
    if _FONTS: return _FONTS
    S=Cfg.SIZE
    try:
        _FONTS={"big":ImageFont.truetype(Cfg.FONT_B,max(16,S//20)),
                "med":ImageFont.truetype(Cfg.FONT_B,max(13,S//28)),
                "small":ImageFont.truetype(Cfg.FONT_R,max(12,S//32))}
    except:
        d=ImageFont.load_default(); _FONTS={"big":d,"med":d,"small":d}
    return _FONTS

def song_line(song,part):
    text=getattr(song,part,"")
    for sep in["...","!","."]:
        idx=text.find(sep)
        if idx>15: return text[:idx].strip()
    return text[:48].strip()

def wrap_text(text: str, max_chars: int) -> list:
    """Coupe le texte en lignes de max_chars caractères."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def draw_ui(img, scene, f_in, song, genre):
    draw = ImageDraw.Draw(img)
    F = get_fonts()
    S = Cfg.SIZE

    # ════════════════════════════════
    # BARRE HAUTE — fond blanc semi-transparent
    # ════════════════════════════════
    top_h = 58
    ov = Image.new("RGBA", (S, top_h), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(ov)
    for yy in range(top_h):
        alpha = int(200 * (1 - yy / top_h) ** 0.6)
        d2.line([(0, yy), (S, yy)], fill=(255, 255, 255, alpha))
    img.paste(Image.alpha_composite(
        img.crop((0, 0, S, top_h)).convert("RGBA"), ov), (0, 0))
    draw = ImageDraw.Draw(img)

    # Acte label — gauche, petit violet
    draw.text((10, 5), scene.acte_label, fill=(110, 70, 200), font=F["small"])
    # Titre scène — gauche, gras
    draw.text((10, 22), scene.titre[:32], fill=(20, 20, 60), font=F["med"])

    # 📍 Lieu — droite, fond pill arrondi
    lieu = DECOR_LABELS.get(scene.decor, f"📍 {scene.decor.capitalize()}")
    try:
        lw = draw.textlength(lieu, font=F["small"])
    except:
        lw = len(lieu) * 7
    lx = S - int(lw) - 18
    draw.rounded_rectangle([lx - 6, 6, S - 8, 26], radius=8, fill=(240, 220, 255))
    draw.text((lx, 8), lieu, fill=(80, 30, 160), font=F["small"])

    # ════════════════════════════════
    # BARRE BASSE — fond noir cinématique
    # ════════════════════════════════
    bot_h = int(S * 0.33)
    ov2 = Image.new("RGBA", (S, bot_h), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(ov2)
    for yy in range(bot_h):
        # fondu progressif du transparent vers noir opaque
        t = (yy / bot_h) ** 0.5
        alpha = int(230 * t)
        d3.line([(0, yy), (S, yy)], fill=(8, 5, 30, alpha))
    img.paste(Image.alpha_composite(
        img.crop((0, S - bot_h, S, S)).convert("RGBA"), ov2), (0, S - bot_h))
    draw = ImageDraw.Draw(img)

    y0 = S - bot_h + 6

    # ♪ Parole de chanson — italique violet clair
    sl = song_line(song, scene.song_part)
    if sl:
        disp = sl[:44] + "…" if len(sl) > 46 else sl
        draw.text((12, y0), f"♪ {disp}", fill=(180, 155, 255), font=F["small"])
        y0 += 20

    # Ligne séparatrice
    draw.line([(12, y0), (S - 12, y0)], fill=(80, 60, 160), width=1)
    y0 += 7

    # 💬 Narration IA — grand texte blanc cassé, multi-lignes
    narr = scene.dialogue
    # Retire le préfixe [Dans...] si présent dans le texte
    if narr.startswith("["):
        end_bracket = narr.find("]")
        if end_bracket != -1:
            narr = narr[end_bracket + 1:].strip()
    
    # Couper plus court (25 au lieu de 30) pour laisser place au personnage à droite
    lines = wrap_text(narr, 25)[:3]
    for i, line in enumerate(lines):
        # Première ligne plus grande
        font = F["med"] if i == 0 else F["small"]
        color = (255, 252, 220) if i == 0 else (210, 200, 240)
        draw.text((12, y0), line, fill=color, font=font)
        y0 += 22 if i == 0 else 18

    # Barre de progression — tout en bas
    prog = f_in / max(1, scene.duree)
    draw.rounded_rectangle([10, S - 9, S - 10, S - 3], radius=3, fill=(40, 30, 90))
    fw = int((S - 20) * prog) + 10
    if fw > 20:
        draw.rounded_rectangle([10, S - 9, fw, S - 3], radius=3, fill=P.UI_BAR)

def easing(t): return 3*t**2-2*t**3
def blend(f1,f2,t): return np.clip(f1*(1-t)+f2*t,0,255).astype(np.uint8)

def render_scene(scene, genre, song, gframe, td):
    frames = []
    S = Cfg.SIZE
    # Le personnage se tient en bas à droite au premier plan
    char_x = int(S * 0.85)
    char_y = int(S * 0.82)
    for f in range(scene.duree):
        img = Image.new("RGBA", (S, S))
        draw = ImageDraw.Draw(img)
        # 1. Image de fond générée si disponible, sinon repli
        if getattr(scene, "bg_img", None) is not None:
            img.paste(scene.bg_img, (0, 0))
        else:
            draw_bg(draw, scene.decor, scene.sky_mood, gframe + f, td)
        
        # 2. Barre d'interface texte
        draw_ui(img, scene, f, song, genre)

        # 3. Personnage au premier plan (par dessus l'image et l'interface)
        draw_char(draw, char_x, char_y, scene.action, scene.emotion, gframe + f, genre)
        
        frames.append(cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR))
    return frames

def render_all(scenes, genre, song, td, pb):
    all_f = []; gf = 0; EF = Cfg.EF; total = len(scenes)
    for i, scene in enumerate(scenes):
        pb.progress((i+1)/total, text=f"🎨 Scène {i+1}/{total} — {scene.titre}")
        sf = render_scene(scene, genre, song, gf, td)
        if all_f and EF > 0:
            prev = all_f[-EF:]; nxt = sf[:EF]
            bl = [blend(prev[j], nxt[j], easing(j/EF)) for j in range(min(EF,len(prev),len(nxt)))]
            all_f[-len(bl):] = bl
        all_f.extend(sf); gf += scene.duree
    pb.progress(1.0, text="✅ Rendu terminé!")
    return all_f

async def _edge_gen(text,voice,rate,pitch,out):
    comm=edge_tts.Communicate(text=text,voice=voice,rate=rate,pitch=pitch)
    await comm.save(out)

def gen_audio(char,song,folder,ph)->str:
    secs=[song.intro,"...",song.acte1,"...",song.acte2,"...",song.refrain1,"...",
          song.acte3,"...",song.acte4,"...",song.refrain2,"...",song.acte5,"...",
          song.acte6,"...",song.outro,"...",song.refrain2]
    txt="  ".join(secs)
    voice=Cfg.VF if char.genre=="fille" else Cfg.VG
    vp=os.path.join(folder,"voix.mp3"); ok=False
    if _EDGE_TTS_OK:
        try:
            ph.info("🎙️ Génération voix neurale..."); asyncio.run(_edge_gen(txt,voice,Cfg.VRATE,Cfg.VPITCH,vp)); ok=True
        except Exception as e: st.warning(f"edge-tts: {e} → gTTS")
    if not ok:
        ph.info("🎙️ Génération voix..."); gTTS(text=txt,lang="fr",slow=True).save(vp)
        
    try:
        ph.info("🎵 Ajout d'une musique douce en fond...")
        from pydub import AudioSegment
        import urllib.request
        
        # Lien vers une musique d'ambiance libre de droits et relaxante
        bgm_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-15.mp3"
        bgm_path = os.path.join(folder, "bgm.mp3")
        
        req = urllib.request.Request(bgm_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp, open(bgm_path, 'wb') as f:
            f.write(resp.read())
            
        voix_audio = AudioSegment.from_file(vp)
        music_audio = AudioSegment.from_file(bgm_path)
        
        # Baisser fortement le volume de la musique (-15 décibels) pour entendre la voix
        music_audio = music_audio - 15
        
        # Si la voix est plus longue que la musique, on répète la boucle musicale
        while len(music_audio) < len(voix_audio):
            music_audio += music_audio
            
        # Couper la musique exactement à la fin de la voix
        music_audio = music_audio[:len(voix_audio)]
        
        # Mixer (superposer) les deux pistes
        mix = voix_audio.overlay(music_audio)
        
        vp_mix = os.path.join(folder, "voix_mix.mp3")
        mix.export(vp_mix, format="mp3")
        return vp_mix
        
    except Exception as e:
        # En cas d'erreur internet sur la musique, on retourne la voix seule.
        return vp

def encode_video(frames,audio,folder,prenom)->str:
    silent=os.path.join(folder,"_s.mp4"); final=os.path.join(folder,f"ANIME_{prenom.upper()}.mp4")
    h,w=frames[0].shape[:2]
    wr=cv2.VideoWriter(silent,cv2.VideoWriter_fourcc(*"mp4v"),Cfg.FPS,(w,h))
    for fr in frames: wr.write(fr)
    wr.release()
    subprocess.run(["ffmpeg","-y","-i",silent,"-i",audio,"-c:v","libx264","-preset","fast",
        "-crf",str(Cfg.CRF),"-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest",final],
        capture_output=True,text=True)
    if os.path.exists(silent): os.remove(silent)
    return final

# ─────────────────────────────────────────
#  CSS PROFESSIONNEL
# ─────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html,body,.stApp,[data-testid="stAppViewContainer"]{
    background:#f0f2f8!important;
    font-family:'Inter',system-ui,sans-serif!important;
}
[data-testid="stHeader"]{background:#ffffff!important;border-bottom:1px solid #e2e8f0;}
[data-testid="stSidebar"]{background:#ffffff!important;border-right:1px solid #e2e8f0;padding-top:1.5rem;}
.block-container{background:transparent!important;padding-top:1.5rem!important;max-width:820px!important;}

/* Typography */
h1,h2,h3{color:#0f172a!important;font-family:'Inter',sans-serif!important;}
p,div,span,label{color:#334155!important;font-family:'Inter',sans-serif!important;}

/* Hero */
.hero{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 60%,#db2777 100%);
    border-radius:20px;padding:2rem 2rem 1.75rem;text-align:center;margin-bottom:1.75rem;}
.hero h1{color:#fff!important;font-size:2rem;font-weight:800;margin:0 0 6px!important;}
.hero p{color:rgba(255,255,255,.85)!important;font-size:.95rem;margin:0!important;}

/* Cards */
.card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;
    padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 6px rgba(0,0,0,.05);}
.card-accent{background:#fff;border:2px solid #6366f1;border-radius:16px;
    padding:1.5rem;margin-bottom:1rem;box-shadow:0 4px 20px rgba(99,102,241,.12);}

/* Section labels */
.sec-label{font-size:.7rem;font-weight:700;color:#64748b;text-transform:uppercase;
    letter-spacing:.08em;margin-bottom:.5rem;display:block;}
.sec-title{font-size:1.05rem;font-weight:700;color:#1e293b;margin-bottom:.75rem;
    display:flex;align-items:center;gap:8px;}

/* Step indicator */
.steps-row{display:flex;align-items:center;justify-content:center;
    gap:0;margin-bottom:2rem;}
.step-dot{width:34px;height:34px;border-radius:50%;display:flex;
    align-items:center;justify-content:center;font-weight:800;font-size:13px;
    border:2px solid #cbd5e1;background:#f8fafc;color:#94a3b8;z-index:1;}
.step-dot.active{background:#6366f1;border-color:#6366f1;color:#fff;
    box-shadow:0 0 0 4px rgba(99,102,241,.18);}
.step-dot.done{background:#22c55e;border-color:#22c55e;color:#fff;}
.step-line{width:52px;height:2px;background:#e2e8f0;margin-bottom:18px;}
.step-line.done{background:#22c55e;}
.step-lbl{font-size:10px;font-weight:700;width:70px;text-align:center;
    color:#94a3b8!important;margin-top:3px;}
.step-lbl.active{color:#6366f1!important;}
.step-lbl.done{color:#16a34a!important;}
.step-col{display:flex;flex-direction:column;align-items:center;gap:3px;}

/* ════════════════════════════════════════
   DEEPSEEK-STYLE CHAT CSS
   ════════════════════════════════════════ */

/* Forcer pleine largeur sur les wrappers Streamlit */
[data-testid="stMarkdownContainer"] {
    width: 100% !important;
    display: block !important;
}
[data-testid="stMarkdownContainer"] > div { width: 100% !important; }

/* Bulles */
.chat-bubble {
    padding: 12px 16px;
    border-radius: 18px;
    font-size: 0.92rem;
    line-height: 1.65;
    word-break: break-word;
    max-width: 75%;
}
.chat-bubble.user {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    color: #ffffff !important;
    border-bottom-right-radius: 4px !important;
    box-shadow: 0 4px 18px rgba(79,70,229,0.28) !important;
    margin-left: auto !important;
}
.chat-bubble.ai {
    background: #ffffff !important;
    color: #1e293b !important;
    border-bottom-left-radius: 4px !important;
    border: 1px solid #e8eaf0 !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06) !important;
    margin-right: auto !important;
}

/* Avatar */
.chat-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}
.chat-avatar.ai-av {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    border: 2px solid #c4b5fd;
}
.chat-avatar.user-av {
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
    border: 2px solid #bae6fd;
}

/* Méta-info */
.chat-meta {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; margin-bottom: 4px; opacity: 0.7;
    color: #64748b !important;
}
.chat-row.user .chat-meta { text-align: right !important; color: #a5b4fc !important; }
.chat-row.ai  .chat-meta { text-align: left !important;  color: #6366f1 !important; }

/* Wrapper contenu (bulle + meta) */
.chat-content {
    display: flex; flex-direction: column;
    max-width: calc(100% - 56px);
}
.chat-row.user .chat-content { align-items: flex-end !important; }
.chat-row.ai  .chat-content { align-items: flex-start !important; }

/* Titre section chat */
.chat-section-header {
    display: flex; align-items: center; gap: 12px;
    background: linear-gradient(135deg, #f5f3ff, #ede9fe);
    border: 1px solid #c4b5fd; border-radius: 14px;
    padding: 14px 18px; margin-bottom: 1.25rem;
}
.chat-section-header .csh-icon {
    width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    display:flex; align-items:center; justify-content:center;
    font-size: 1.4rem; flex-shrink:0;
    box-shadow: 0 3px 10px rgba(99,102,241,0.3);
}
.chat-section-header .csh-title {
    font-size: 1rem; font-weight: 800; color: #3730a3 !important; margin: 0 !important;
}
.chat-section-header .csh-sub {
    font-size: 0.78rem; color: #6d28d9 !important; margin-top: 2px;
}

/* Char card */
.char-pill{display:inline-flex;align-items:center;gap:6px;
    background:#ede9fe;border:1px solid #c4b5fd;border-radius:99px;
    padding:4px 12px;font-size:.8rem;font-weight:700;color:#5b21b6;margin:3px 2px;}
.danger-pill{background:#fef2f2;border:1px solid #fca5a5;
    border-radius:99px;padding:4px 12px;font-size:.8rem;font-weight:700;color:#dc2626;
    display:inline-flex;align-items:center;gap:5px;margin:3px 2px;}

/* Tip row */
.tip-row{display:flex;gap:8px;flex-wrap:wrap;margin:.5rem 0;}
.tip-chip{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
    padding:5px 10px;font-size:.8rem;color:#1e40af;font-weight:600;}

/* Song part */
.song-blk{background:#fafafa;border:1px solid #e2e8f0;border-radius:10px;
    padding:.875rem 1rem;margin-bottom:6px;}
.song-lbl{font-size:.68rem;font-weight:800;color:#6366f1;text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:3px;}
.song-txt{font-size:.86rem;color:#475569;line-height:1.65;font-style:italic;}

/* Sidebar */
.sb-title{font-size:.95rem;font-weight:800;color:#1e293b;margin-bottom:.5rem;
    display:flex;align-items:center;gap:8px;}
.sb-note{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
    padding:8px 10px;font-size:.78rem;color:#1d4ed8;margin-top:.5rem;line-height:1.5;}
.sb-step{font-size:.76rem;color:#475569;padding:3px 0;display:flex;
    align-items:flex-start;gap:6px;}

/* Buttons */
.stButton>button{border-radius:10px!important;font-weight:700!important;
    font-size:.88rem!important;transition:all .2s!important;}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#6366f1,#8b5cf6)!important;
    color:#fff!important;border:none!important;
    box-shadow:0 3px 12px rgba(99,102,241,.3)!important;}
.stButton>button[kind="primary"]:hover{
    transform:translateY(-2px)!important;
    box-shadow:0 6px 18px rgba(99,102,241,.4)!important;}

/* Inputs */
.stTextArea>div>div>textarea,.stTextInput>div>div>input{
    background:#fff!important;border:1.5px solid #e2e8f0!important;
    border-radius:10px!important;font-size:.93rem!important;color:#1e293b!important;}
.stTextArea>div>div>textarea:focus,.stTextInput>div>div>input:focus{
    border-color:#6366f1!important;
    box-shadow:0 0 0 3px rgba(99,102,241,.1)!important;}

/* Progress */
.stProgress>div>div>div{background:linear-gradient(90deg,#6366f1,#8b5cf6)!important;}

/* Misc */
hr{border-color:#e2e8f0!important;}
.stAlert{border-radius:12px!important;}
#MainMenu,footer{visibility:hidden;}
</style>
"""

# ─────────────────────────────────────────
#  HELPERS UI
# ─────────────────────────────────────────
def stepper(cur:int)->str:
    labels=["📝 La bêtise","🎬 Scénario","🎉 Vidéo"]
    icons=["📝","🎬","🎉"]
    parts=[]
    for i in range(1,4):
        if i<cur:     dc,lc2,nt="done","done","✓"
        elif i==cur:  dc,lc2,nt="active","active",icons[i-1]
        else:         dc,lc2,nt="","",str(i)
        parts.append(f'<div class="step-col"><div class="step-dot {dc}">{nt}</div>'
                     f'<div class="step-lbl {lc2}">{labels[i-1]}</div></div>')
        if i<3:
            ld="done"if i<cur else ""
            parts.append(f'<div class="step-line {ld}"></div>')
    return f'<div class="steps-row">{"".join(parts)}</div>'


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    st.set_page_config(page_title="Studio Animé Éducatif",page_icon="🎬",
                       layout="centered",initial_sidebar_state="expanded")
    st.markdown(CSS,unsafe_allow_html=True)

    # ── SESSION ──
    defaults={"step":1,"api_key":"","betise":"","val":None,
              "scenario":None,"char":None,"song":None,"narrations":[],"img_prompts":[],
              "theme":"general","show_key":False,"analyzing":False,
              "confirmed_yes":False,"confirmed_no":False,
              "chat_history":[],"editing_index":None,"editing_content":""}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v

    # ══════════════════════════════════════
    #  SIDEBAR — CLÉ API GROQ
    # ══════════════════════════════════════
    with st.sidebar:
        st.markdown('<div class="sb-title">🔑 Clé API Groq</div>',unsafe_allow_html=True)
        kt="text"if st.session_state.show_key else"password"
        key=st.text_input("Clé",value=st.session_state.api_key,type=kt,
            placeholder="gsk_...",label_visibility="collapsed")
        st.session_state.api_key=key
        c1,c2=st.columns([3,1])
        with c2:
            if st.button("👁"if not st.session_state.show_key else"🙈",key="sbv",help="Afficher/Masquer"):
                st.session_state.show_key=not st.session_state.show_key; st.rerun()
        valid_key=bool(key and key.strip().startswith("gsk_"))
        if valid_key: st.success("✅ Clé valide")
        else: st.warning("Clé non renseignée")

        st.markdown('<div class="sb-note">🆓 Clé <b>100% gratuite</b> sur<br>'
            '<a href="https://console.groq.com" target="_blank">console.groq.com</a><br>'
            '→ <b>API Keys → Create API Key</b><br><br>'
            '🔒 Jamais sauvegardée.</div>',unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**📋 Guide rapide**")
        for i,(ic,txt) in enumerate([
            ("1️⃣","Copie ta clé Groq ci-dessus"),
            ("2️⃣","Décris la bêtise de ton enfant"),
            ("3️⃣","L'IA analyse et génère"),
            ("4️⃣","Télécharge la vidéo MP4"),
        ],1):
            st.markdown(f'<div class="sb-step">{ic} <span>{txt}</span></div>',unsafe_allow_html=True)

        if st.session_state.step>1:
            st.markdown("---")
            if st.button("🔄 Recommencer",use_container_width=True):
                for k in["step","betise","val","scenario","char","song","narrations","img_prompts","theme","confirmed_yes","confirmed_no"]:
                    st.session_state[k]=1 if k=="step" else "general"if k=="theme" else[]if k in["narrations","img_prompts"] else""if k=="betise" else False if k in["confirmed_yes","confirmed_no"] else None
                st.rerun()

    # ── HÉRO ──
    st.markdown("""<div class="hero">
        <h1>🎬 Studio Animé Éducatif</h1>
        <p>Transforme la bêtise de ton enfant en dessin animé éducatif personnalisé ✨</p>
    </div>""",unsafe_allow_html=True)

    st.markdown(stepper(st.session_state.step),unsafe_allow_html=True)

    # ══════════════════════════════════════
    #  ÉTAPE 1 — CHAT PÉDAGOGIQUE CONVERSATIONNEL
    # ══════════════════════════════════════
    if st.session_state.step == 1:
        import datetime as _dt
        import html as _html

        def _ts():
            return _dt.datetime.now().strftime("%H:%M")

        def make_ai_bubble(html_content, ts=""):
            """Retourne le HTML d'une bulle IA (gauche)."""
            return (
                f'<div class="chat-row ai">'
                f'<div class="chat-avatar ai-av">🤖</div>'
                f'<div class="chat-content">'
                f'<div class="chat-meta ai">Assistant Pédagogique{" · "+ts if ts else ""}</div>'
                f'<div class="chat-bubble ai">{html_content}</div>'
                f'</div></div>'
            )

        def make_user_bubble(html_content, ts=""):
            """Retourne le HTML d'une bulle parent (droite)."""
            return (
                f'<div class="chat-row user">'
                f'<div class="chat-avatar user-av">👤</div>'
                f'<div class="chat-content">'
                f'<div class="chat-meta user">Vous{" · "+ts if ts else ""}</div>'
                f'<div class="chat-bubble user">{html_content}</div>'
                f'</div></div>'
            )

        # EN-TÊTE
        st.markdown(
            '<div class="chat-section-header">'
            '<div class="csh-icon">🎓</div>'
            '<div>'
            '<div class="csh-title">Assistant Pédagogique</div>'
            '<div class="csh-sub">Discutez librement · Détection automatique des situations de danger</div>'
            '</div></div>',
            unsafe_allow_html=True
        )

        # ─ Fonctions de bulles DeepSeek ─
        def ds_ai_bubble(content, ts=""):
            return (
                '<div class="ds-msg-ai">'
                '<div class="ds-avatar-ai">🤖</div>'
                '<div class="ds-content">'
                f'<div class="ds-bubble-ai">{content}</div>'
                + (f'<span class="ds-time">{ts}</span>' if ts else '') +
                '</div></div>'
            )

        def ds_user_bubble(content, ts=""):
            return (
                '<div class="ds-msg-user">'
                '<div class="ds-content">'
                f'<div class="ds-bubble-user">{content}</div>'
                + (f'<span class="ds-time">Vous · {ts}</span>' if ts else '') +
                '</div></div>'
            )

        # ─ Message d’accueil IA ─
        greeting = (
            "<b>Bonjour ! 👋 Je suis votre Assistant Pédagogique.</b><br>"
            "<span style='font-size:0.88rem;opacity:0.85;'>"
            "Parlez-moi librement — si vous décrivez un comportement dangereux de votre enfant,"
            " je génère automatiquement un scénario éducatif animé personnalisé. ✨"
            "</span>"
        )
        st.markdown(ds_ai_bubble(greeting), unsafe_allow_html=True)

        # ─ Historique : rendu message par message avec édition inline ─
        _ei = st.session_state.get("editing_index", None)
        for i, msg in enumerate(st.session_state.chat_history):
            txt = _html.escape(msg["content"]).replace("\n", "<br>")
            ts  = msg.get("ts", "")

            if msg["role"] == "ai":
                st.markdown(ds_ai_bubble(txt, ts), unsafe_allow_html=True)

            else:  # user
                if _ei == i:
                    # ─ MODE ÉDITION INLINE ─
                    _sp, _edit_zone = st.columns([1, 5])
                    with _edit_zone:
                        edited = st.text_area(
                            "Modifier",
                            value=st.session_state.editing_content,
                            height=90, label_visibility="collapsed",
                            key=f"inline_edit_{i}"
                        )
                        st.session_state.editing_content = edited
                        _ca, _cc = st.columns([1, 1])
                        with _cc:
                            if st.button("✓ Confirmer", key=f"confirm_{i}",
                                         type="primary", use_container_width=True):
                                new_txt = st.session_state.editing_content.strip()
                                if new_txt:
                                    # Met à jour le message dans l'historique
                                    st.session_state.chat_history[i]["content"] = new_txt
                                    # Supprime les messages suivants
                                    st.session_state.chat_history = \
                                        st.session_state.chat_history[:i+1]
                                    st.session_state.editing_index = None
                                    st.session_state.editing_content = ""
                                    st.session_state.val = None
                                    # Re-soumet à l'IA
                                    with st.spinner("🤖 Analyse du message modifié…"):
                                        try:
                                            res = chat_ai(new_txt, st.session_state.api_key)
                                            reply = res.get("response", "Bien reçu !")
                                            st.session_state.chat_history.append(
                                                {"role":"ai","content":reply,"ts":_ts()})
                                            st.session_state.val = res if res.get("type")=="scenario" else None
                                            if res.get("theme") in THEMES:
                                                st.session_state.theme = res["theme"]
                                        except Exception as e:
                                            st.error(f"Erreur : {e}")
                                    st.rerun()
                        with _ca:
                            if st.button("✕ Annuler", key=f"cancel_{i}",
                                         use_container_width=True):
                                st.session_state.editing_index = None
                                st.session_state.editing_content = ""
                                st.rerun()
                else:
                    # ─ AFFICHAGE NORMAL bulle parent ─
                    _sp, _bcol = st.columns([1, 6])
                    with _bcol:
                        _editbtn, _bubbcol = st.columns([0.4, 5.6])
                        with _editbtn:
                            if st.button("✏️", key=f"edit_msg_{i}",
                                         help="Modifier ce message"):
                                st.session_state.editing_index = i
                                st.session_state.editing_content = msg["content"]
                                st.rerun()
                        with _bubbcol:
                            st.markdown(ds_user_bubble(txt, ts), unsafe_allow_html=True)



        # ══════════════════════════════════════
        # BOUTONS D'ACTION — si dernier msg IA est un scénario
        # ══════════════════════════════════════
        last_val = st.session_state.val
        if last_val and last_val.get("type") == "scenario" and last_val.get("valide"):
            v = last_val
            sugg = v.get("suggestions", [])

            st.markdown(
                "<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);"
                "border:1px solid #86efac;border-radius:12px;padding:12px 16px;"
                "margin-top:12px;font-size:0.88rem;color:#166534;'>"
                f"<b>🎬 Scénario prêt :</b> {v.get('prenom','?')} · {v.get('age','')} ans · ⚠️ {v.get('danger','')}"
                "</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

            if sugg:
                for sid, s in enumerate(sugg[:2]):
                    if st.button(f"➕ Enrichir : {s}", key=f"add_sugg_{sid}",
                                 use_container_width=True):
                        new_msg = st.session_state.betise.strip()
                        if new_msg and not new_msg[-1] in ".,!?": new_msg += ","
                        new_msg = (new_msg + " " + s).strip()
                        st.session_state.betise = new_msg
                        _now = _ts()
                        st.session_state.chat_history.append(
                            {"role":"user","content":new_msg,"ts":_now})
                        with st.spinner("🤖 Mise à jour…"):
                            try:
                                res = chat_ai(new_msg, st.session_state.api_key)
                                reply = res.get("response", "")
                                st.session_state.chat_history.append(
                                    {"role":"ai","content":reply,"ts":_ts()})
                                st.session_state.val = res
                                if res.get("theme") in THEMES:
                                    st.session_state.theme = res["theme"]
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                        st.rerun()

            c_gen, c_new = st.columns([3, 1])
            with c_gen:
                if st.button("🎬 Générer le dessin animé éducatif !",
                             type="primary", use_container_width=True):
                    with st.spinner("🎵 Génération du scénario…"):
                        try:
                            betise_src = st.session_state.betise
                            data = scenario_ai(betise_src, v, st.session_state.api_key)
                            st.session_state.scenario = data
                            char, song, narrations, img_prompts = parse_scenario(data)
                            st.session_state.char = char
                            st.session_state.song = song
                            st.session_state.narrations = narrations
                            st.session_state.img_prompts = img_prompts
                            st.session_state.step = 2
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("Format JSON invalide.")
                        except Exception as e:
                            st.error(f"Erreur : {e}")
            with c_new:
                if st.button("🔄 Réinterpréter", use_container_width=True):
                    with st.spinner("🤖 Nouvelle interprétation…"):
                        try:
                            res = chat_ai(st.session_state.betise,
                                          st.session_state.api_key)
                            reply = res.get("response", "")
                            # Met à jour le dernier msg IA dans l'historique
                            if st.session_state.chat_history and \
                               st.session_state.chat_history[-1]["role"] == "ai":
                                st.session_state.chat_history[-1]["content"] = reply
                            else:
                                st.session_state.chat_history.append(
                                    {"role":"ai","content":reply,"ts":_ts()})
                            st.session_state.val = res
                            if res.get("theme") in THEMES:
                                st.session_state.theme = res["theme"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

        # ══════════════════════════════════════
        # ZONE DE SAISIE STYLE DEEPSEEK
        # ══════════════════════════════════════
        st.markdown(
            "<div style='margin-top:18px;border-top:1px solid #f1f5f9;padding-top:16px;'></div>",
            unsafe_allow_html=True
        )

        user_input = st.text_area(
            "Votre message",
            value=st.session_state.betise,
            placeholder="Écrivez votre message… (Bonjour / Mon fils Adam 5 ans touche les prises / ...)",
            height=90, label_visibility="collapsed", key="main_input"
        )
        if user_input != st.session_state.betise:
            st.session_state.betise = user_input

        # Bouton Envoyer uniquement (style DeepSeek)
        _, _sbtn = st.columns([5, 1])
        with _sbtn:
            if st.button("↗ Envoyer", type="primary",
                         use_container_width=True, key="btn_envoyer"):
                if not st.session_state.api_key.strip():
                    st.error("⚠️ Clé API Groq manquante (barre latérale).")
                elif not st.session_state.betise.strip():
                    st.error("⚠️ Écris ton message.")
                elif not _GROQ_OK:
                    st.error("La bibliothèque `groq` n'est pas installée.")
                else:
                    _now = _ts()
                    msg_texte = st.session_state.betise.strip()
                    st.session_state.chat_history.append(
                        {"role": "user", "content": msg_texte, "ts": _now})
                    with st.spinner("🤖 L'IA réfléchit…"):
                        try:
                            res = chat_ai(msg_texte, st.session_state.api_key)
                            reply = res.get("response", "Je suis là !")
                            st.session_state.chat_history.append(
                                {"role": "ai", "content": reply, "ts": _ts()})
                            st.session_state.val = res if res.get("type") == "scenario" else None
                            if res.get("theme") in THEMES:
                                st.session_state.theme = res["theme"]
                            st.session_state.betise = ""
                            st.rerun()
                        except Exception as e:
                            st.session_state.chat_history.pop()
                            st.error(f"Erreur API Groq : {e}")

        # ── SUGGESTIONS RAPIDES (chips) ──
        st.markdown(
            "<div style='margin-top:14px;'>"
            "<span style='font-size:0.7rem;font-weight:700;color:#94a3b8;"
            "text-transform:uppercase;letter-spacing:0.06em;'>💡 Suggestions rapides</span>"
            "</div>",
            unsafe_allow_html=True
        )
        ex_cols = st.columns(len(EXAMPLES))
        for idx, ex in enumerate(EXAMPLES):
            with ex_cols[idx]:
                if st.button(
                    f"{ex['icon']} {ex['label']}", key=f"ex_{idx}",
                    use_container_width=True, help=ex["text"]
                ):
                    st.session_state.betise = ex["text"]
                    st.session_state.theme = ex["theme"]
                    st.rerun()



    # ══════════════════════════════════════
    #  ÉTAPE 2 — SCÉNARIO
    # ══════════════════════════════════════
    elif st.session_state.step==2:
        char=st.session_state.char; song=st.session_state.song
        data=st.session_state.scenario
        t=THEMES.get(st.session_state.theme,THEMES["general"])
        if not char or not song:
            st.error("Données manquantes."); st.session_state.step=1; st.rerun()

        # Carte personnage
        st.markdown(f"""<div class="card-accent">
        <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
            <div style="width:60px;height:60px;border-radius:50%;
                 background:linear-gradient(135deg,{t['color']},#ec4899);
                 display:flex;align-items:center;justify-content:center;
                 font-size:1.8rem;flex-shrink:0;">
                 {'👧'if char.genre=='fille'else'👦'}</div>
            <div style="flex:1;min-width:140px;">
                <div style="font-size:1.4rem;font-weight:800;color:#0f172a;">{char.prenom}</div>
                <div style="font-size:.85rem;color:#64748b;">{char.age} ans · {char.genre}</div>
                <div style="margin-top:6px;">
                    <span class="danger-pill">⚠️ {data.get('danger_court','')}</span>
                    <span class="char-pill">{t['label']}</span>
                </div>
            </div>
            <div style="flex:1;min-width:180px;background:#f8fafc;border-radius:10px;
                 padding:10px;border:1px solid #e2e8f0;">
                <span class="sec-label">🎨 Décor &amp; Ambiance</span>
                <div style="font-size:.85rem;color:#374151;">{data.get('decor_principal','')}</div>
                <div style="font-size:.8rem;color:{t['color']};font-weight:700;margin-top:3px;">
                    🎨 {data.get('ambiance_couleur','')}</div>
            </div>
        </div>
        <div style="margin-top:10px;border-top:1px solid #e2e8f0;padding-top:10px;">
            <span style="font-size:.85rem;font-weight:700;color:#4f46e5;">🎵 {song.titre}</span>
        </div>
        </div>""",unsafe_allow_html=True)

        # Chanson
        with st.expander("🎵 Voir la chanson complète générée",expanded=False):
            for lbl,txt in [
                ("🎵 Introduction",song.intro),("📖 Acte I — Vie normale",song.acte1),
                ("😮 Acte II — La tentation",song.acte2),("🚨 Refrain 1 — Avertissement",song.refrain1),
                ("⚠️ Acte III — La bêtise",song.acte3),("💥 Acte IV — Conséquence",song.acte4),
                ("💡 Refrain 2 — La leçon",song.refrain2),("😢 Acte V — Il comprend",song.acte5),
                ("🤝 Acte VI — La promesse",song.acte6),("🫵 Message final",song.outro)]:
                st.markdown(f'<div class="song-blk"><div class="song-lbl">{lbl}</div>'
                    f'<div class="song-txt">{txt}</div></div>',unsafe_allow_html=True)

        # Aperçu scènes
        sc_prev=[("🏠","Intro"),("🌳","Acte I"),("😮","Acte II"),("🚨","Refrain"),
                 ("⚠️","Acte III"),("💥","Acte IV"),("💡","Refrain"),("😢","Acte V"),
                 ("🤝","Acte VI"),("🎉","Fin")]
        cols5=st.columns(5)
        for i,(ic,nm) in enumerate(sc_prev):
            with cols5[i%5]:
                st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;'
                    f'border-radius:10px;padding:10px 4px;text-align:center;margin-bottom:6px;">'
                    f'<div style="font-size:1.3rem;">{ic}</div>'
                    f'<div style="font-size:.64rem;font-weight:700;color:#64748b;margin-top:3px;">{nm}</div>'
                    f'</div>',unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)
        cb,cg=st.columns([1,2])
        with cb:
            if st.button("← Modifier",use_container_width=True):
                st.session_state.step=1; st.session_state.val=None; st.rerun()
        with cg:
            if st.button("🎬 Générer la vidéo maintenant!",type="primary",use_container_width=True):
                st.session_state.step=3; st.rerun()

    # ══════════════════════════════════════
    #  ÉTAPE 3 — GÉNÉRATION VIDÉO
    # ══════════════════════════════════════
    elif st.session_state.step==3:
        char=st.session_state.char; song=st.session_state.song
        data=st.session_state.scenario
        td=THEMES.get(st.session_state.theme,THEMES["general"])
        if not char or not song:
            st.error("Données manquantes."); st.session_state.step=1; st.rerun()

        st.markdown(f"""<div class="card" style="display:flex;align-items:center;gap:14px;
            padding:1rem 1.25rem;">
            <div style="font-size:2.2rem;">{'👧'if char.genre=='fille'else'👦'}</div>
            <div>
                <div style="font-weight:800;font-size:1.1rem;color:#0f172a;">
                    {char.prenom} · {char.age} ans</div>
                <div style="font-size:.84rem;color:#64748b;">🎵 {song.titre}</div>
            </div>
        </div>""",unsafe_allow_html=True)

        with st.status("⚙️ Génération en cours...",expanded=True) as status:
            scenes=build_scenes(char,song,st.session_state.theme,st.session_state.narrations,st.session_state.img_prompts)
            
            st.write("🖼️ Génération des décors avec l'IA (Images)...")
            import urllib.request, urllib.parse
            import time
            pb_bg = st.progress(0, text="Téléchargement garanti des images IA (cela prendra environ 1 minute)…")
            for i, scene in enumerate(scenes):
                # On s'assure d'obtenir une image générée par l'IA (pollinations) pour chaque scène
                image_recue = False
                for tentatives in range(10): # On insiste jusqu'à 10 fois pour éviter le fond basique
                    try:
                        prompt = f"{scene.image_prompt}, 2d flat vector illustration, colorful children book style, cute, no text, no people"
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={Cfg.SIZE}&height={Cfg.SIZE}&nologo=true&seed={42+i}"
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            scene.bg_img = Image.open(resp).convert("RGBA").resize((Cfg.SIZE, Cfg.SIZE))
                            image_recue = True
                            break
                    except Exception as e:
                        time.sleep(1.5) # Le serveur bloque ? On attend 1.5s et on recommence.
                
                if not image_recue:
                    scene.bg_img = None
                pb_bg.progress((i+1)/len(scenes), text=f"Décor IA {i+1}/{len(scenes)}")

            st.write("🎨 Rendu vidéo frame par frame...")
            pb=st.progress(0,text="Démarrage…")
            frames=render_all(scenes,char.genre,song,td,pb)

            st.write("🎙️ Génération de la voix…")
            aph=st.empty()
            with tempfile.TemporaryDirectory() as tmpdir:
                audio=gen_audio(char,song,tmpdir,aph); aph.empty()
                st.write("⚙️ Encodage MP4…")
                fp=encode_video(frames,audio,tmpdir,char.prenom)
                if not os.path.exists(fp):
                    st.error("❌ Erreur encodage. Vérifie que ffmpeg est installé."); st.stop()
                with open(fp,"rb")as fv: vb=fv.read()
            status.update(label="✅ Vidéo prête!",state="complete",expanded=False)

        st.success(f"🎉 La vidéo de **{char.prenom}** est prête!")
        st.video(vb)
        danger_slug=data.get("danger_court","").replace(" ","_")
        st.download_button(
            label=f"💾 Télécharger la vidéo — {char.prenom}.mp4",
            data=vb,
            file_name=f"anime_{char.prenom.lower()}_{danger_slug}.mp4",
            mime="video/mp4",use_container_width=True,type="primary")

        st.markdown("---")
        c1,c2=st.columns(2)
        with c1:
            if st.button("🔄 Créer une nouvelle vidéo",use_container_width=True,type="primary"):
                for k in["step","betise","val","scenario","char","song","narrations","img_prompts","theme","confirmed_yes","confirmed_no"]:
                    st.session_state[k]=1 if k=="step" else "general" if k=="theme" else [] if k in["narrations","img_prompts"] else "" if k=="betise" else False if k in["confirmed_yes","confirmed_no"] else None
                st.rerun()
        with c2:
            st.info("💡 Partage cette vidéo avec ton enfant pour apprendre en s'amusant!")

    # ── Footer ──
    st.markdown("---")
    st.markdown("<p style='text-align:center;font-size:.76rem;color:#94a3b8;'>"
        "Studio Animé Éducatif v3 · Groq AI (100% gratuit) · "
        "Pour les enfants de 3 à 8 ans · Bienveillant &amp; Éducatif</p>",
        unsafe_allow_html=True)


if __name__=="__main__":
    main()
