"""
╔══════════════════════════════════════════════════════════╗
║   ANIME EDUCATIF STUDIO — Streamlit App                 ║
║   Le parent écrit la bêtise → vidéo générée auto       ║
╚══════════════════════════════════════════════════════════╝
"""

import streamlit as st
import subprocess, sys, os, re, math, random, asyncio, json, tempfile
from datetime import datetime
from dataclasses import dataclass
from typing import List
import warnings
warnings.filterwarnings("ignore")

# ── Installation auto des dépendances ────────────────────────────────────────
@st.cache_resource
def install_deps():
    deps = ["anthropic", "edge-tts", "gtts", "pydub", "opencv-python", "pillow", "numpy"]
    for pkg in deps:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], capture_output=True)
    subprocess.run(["apt-get", "install", "-qq", "-y", "ffmpeg"], capture_output=True)
    return True

install_deps()

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
import anthropic

try:
    import edge_tts
    _EDGE_TTS_OK = True
except:
    _EDGE_TTS_OK = False

try:
    from pydub import AudioSegment
    _PYDUB_OK = True
except:
    _PYDUB_OK = False


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
class Config:
    FPS          = 24
    SIZE         = 512           # réduit pour Streamlit Cloud (moins de RAM)
    CRF          = 23
    EASE_FRAMES  = 6
    FONT_DIR     = "/usr/share/fonts/truetype/dejavu/"
    FONT_BOLD    = FONT_DIR + "DejaVuSans-Bold.ttf"
    FONT_REGULAR = FONT_DIR + "DejaVuSans.ttf"
    VOICE_FILLE  = "fr-FR-DeniseNeural"
    VOICE_GARCON = "fr-FR-HenriNeural"
    VOICE_RATE   = "-20%"
    VOICE_PITCH  = "+5Hz"
    AI_MODEL     = "claude-sonnet-4-20250514"
    AI_MAX_TOKENS = 2048


# ══════════════════════════════════════════════════════════════════════════════
#  DATACLASSES
# ══════════════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════════════
#  GÉNÉRATION IA
# ══════════════════════════════════════════════════════════════════════════════
SCENARIO_PROMPT = """Tu es un auteur de livres éducatifs pour enfants de 3 à 8 ans.
Un parent t'écrit une phrase décrivant une bêtise dangereuse que fait son enfant.
Génère une chanson narrative complète en français.

RÈGLES :
- La chanson RACONTE une histoire du début à la fin
- Le personnage a le VRAI prénom de l'enfant
- Ton bienveillant, musical, avec rimes si possible
- Chaque section : 3 à 5 phrases courtes

Réponds UNIQUEMENT avec un JSON valide, sans markdown :
{
  "prenom": "prénom extrait",
  "age": 5,
  "genre": "garçon ou fille",
  "danger_court": "en 3 mots max",
  "song": {
    "titre": "La Chanson de [prénom] et [danger]",
    "intro": "2 phrases d'accroche musicale",
    "acte1": "Vie normale de l'enfant (3-4 phrases)",
    "acte2": "Il découvre l'objet dangereux (3-4 phrases)",
    "refrain1": "Refrain d'avertissement avec non non non (3-4 phrases)",
    "acte3": "Il commet la bêtise (2-3 phrases)",
    "acte4": "La conséquence dramatique (3-4 phrases)",
    "refrain2": "Refrain de la leçon (3-4 phrases)",
    "acte5": "Il comprend et regrette (3-4 phrases)",
    "acte6": "Il fait une promesse (3-4 phrases)",
    "outro": "Message à l'enfant spectateur (2-3 phrases)"
  }
}"""


def generate_with_ai(probleme: str, api_key: str):
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=Config.AI_MODEL,
        max_tokens=Config.AI_MAX_TOKENS,
        messages=[{"role": "user", "content": f"{SCENARIO_PROMPT}\n\nPhrase du parent : {probleme}"}]
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)

    char = Character(prenom=data["prenom"], age=int(data["age"]), genre=data["genre"])
    s = data["song"]
    song = SongData(
        titre=s["titre"], intro=s["intro"], acte1=s["acte1"], acte2=s["acte2"],
        refrain1=s["refrain1"], acte3=s["acte3"], acte4=s["acte4"],
        refrain2=s["refrain2"], acte5=s["acte5"], acte6=s["acte6"], outro=s["outro"]
    )
    return char, song, data.get("danger_court", "")


# ══════════════════════════════════════════════════════════════════════════════
#  SCÈNES
# ══════════════════════════════════════════════════════════════════════════════
def build_scenes(char: Character, song: SongData) -> List[Scene]:
    p = char.prenom
    fps = Config.FPS
    return [
        Scene("Introduction",      "Intro",                    "parc",   "saute_joie",      "heureux",   f"La chanson de {p} commence !",    fps*5,  "day",    "intro"),
        Scene("La vie normale",    "Acte I",                   "parc",   "court_vite",      "heureux",   f"{p} joue, rit, tout va bien !",   fps*5,  "day",    "acte1"),
        Scene("Une belle journée", "Acte I",                   "maison", "marche_content",  "heureux",   f"{p} est heureux chaque jour.",    fps*4,  "golden", "acte1"),
        Scene("Oh… qu'est-ce ?",   "Acte II - La tentation",   "maison", "decouvre_surpris","curieux",   f"Quelque chose attire {p}…",       fps*5,  "golden", "acte2"),
        Scene("Une idée...",       "Acte II - La tentation",   "maison", "hesite_balance",  "penseur",   f"Juste une petite fois…",          fps*4,  "golden", "acte2"),
        Scene("ATTENTION !",       "Refrain - Avertissement",  "parc",   "appelle_gestes",  "effraye",   f"Non non non ! C'est dangereux !", fps*5,  "day",    "refrain1"),
        Scene("NON NON NON !",     "Refrain - Avertissement",  "parc",   "saute_peur",      "effraye",   f"Arrête ! Appelle un adulte !",    fps*4,  "day",    "refrain1"),
        Scene("La bêtise !",       "Acte III - La faute",      "maison", "fait_betise_saute","curieux",  f"{p} n'écoute pas… il le fait !",  fps*6,  "dusk",   "acte3"),
        Scene("Les conséquences",  "Acte IV - Le danger",      "danger", "court_panique",   "effraye",   f"C'est dangereux ! {p} a peur !",  fps*6,  "dusk",   "acte4"),
        Scene("AU SECOURS !",      "Acte IV - Le danger",      "danger", "appelle_gestes",  "effraye",   f"AU SECOURS ! MAMAN ! PAPA !",     fps*5,  "dusk",   "acte4"),
        Scene("La leçon",          "Refrain - La leçon",       "parc",   "ecoute_hoche",    "desole",    f"Voilà ce qu'il faut faire.",      fps*5,  "day",    "refrain2"),
        Scene(f"{p} comprend",     "Acte V - Compréhension",   "parc",   "pleure_assise",   "triste",    f"{p} pleure… il comprend.",        fps*6,  "day",    "acte5"),
        Scene("La promesse",       "Acte VI - Résolution",     "parc",   "saute_promesse",  "determine", f"{p} fait une promesse !",         fps*5,  "day",    "acte6"),
        Scene("Et toi ?",          "Message final",            "parc",   "pointe_enfant",   "heureux",   f"{p} te parle à toi !",            fps*5,  "day",    "outro"),
        Scene("À bientôt !",       "Message final",            "parc",   "salue_saute",     "fier",      f"Bravo d'avoir regardé !",         fps*4,  "day",    "outro"),
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  PALETTE
# ══════════════════════════════════════════════════════════════════════════════
class P:
    SKY_TOP=(100,160,255); SKY_BOT=(200,230,255)
    DUSK_TOP=(220,80,50);  DUSK_BOT=(150,60,40)
    GOLD_TOP=(255,180,60); GOLD_BOT=(255,220,120)
    GRASS=(70,175,70);     GRASS_S=(50,130,50)
    WALL=(255,235,210);    ROOF=(185,80,60)
    DOOR=(110,65,35);      WINDOW=(180,220,255)
    SKIN=(255,232,205);    SKIN_S=(225,190,155)
    CHEEK=(255,175,165);   HAIR_B=(55,38,18)
    HAIR_G=(195,135,70);   SHIRT_B=(70,130,255)
    SHIRT_G=(255,120,175); PANTS=(45,85,195)
    SHOE=(175,48,48);      EYE_B=(80,160,255)
    EYE_G=(255,100,195);   WHITE=(255,255,255)
    OUTLINE=(30,20,10);    SUN=(255,245,100)
    FLAME_O=(255,110,0);   FLAME_C=(255,230,80)
    TEAR=(90,195,255);     STAR=(255,225,45)
    UI_BG=(12,12,38);      UI_TFG=(255,255,200)
    UI_DFG=(255,250,130);  UI_BAR=(90,200,255)
    SONG_BG=(20,10,50);    SONG_FG=(255,240,100)


def lerp(a,b,t): return a+(b-a)*t
def lc(c1,c2,t): return tuple(int(lerp(a,b,t)) for a,b in zip(c1,c2))

def grad(draw,x0,y0,x1,y1,tc,bc):
    for y in range(y0,y1):
        t=(y-y0)/max(1,y1-y0)
        draw.line([(x0,y),(x1,y)],fill=lc(tc,bc,t))

def sky_colors(mood):
    if mood=="dusk":   return P.DUSK_TOP, P.DUSK_BOT
    if mood=="golden": return P.GOLD_TOP, P.GOLD_BOT
    return P.SKY_TOP, P.SKY_BOT

def draw_bg(draw, decor, mood, frame):
    S=Config.SIZE
    tc,bc=sky_colors(mood)
    grad(draw,0,0,S,int(S*0.64),tc,bc)
    # Soleil
    if mood not in("dusk",):
        sx,sy=int(S*0.85),int(S*0.09)
        draw.ellipse([sx-20,sy-20,sx+20,sy+20],fill=P.SUN)
    # Sol
    draw.rectangle([0,int(S*0.64),S,S],fill=P.GRASS_S if mood=="dusk" else P.GRASS)
    # Fleurs
    if mood!="dusk":
        for i in range(5):
            fx=40+i*int(S/5)+int(4*math.sin(frame*0.02+i))
            fy=int(S*0.645)
            for pp in range(5):
                a=math.radians(pp*72)
                draw.ellipse([fx+int(7*math.cos(a))-3,fy+int(7*math.sin(a))-3,
                              fx+int(7*math.cos(a))+3,fy+int(7*math.sin(a))+3],fill=P.WHITE)
            draw.ellipse([fx-4,fy-4,fx+4,fy+4],fill=(255,210,50))
    # Arbre
    tx,ty=int(S*0.83),int(S*0.64)
    draw.rectangle([tx-8,ty-int(S*0.22),tx+8,ty],fill=(85,52,28))
    draw.ellipse([tx-int(S*0.09),ty-int(S*0.32),tx+int(S*0.09),ty-int(S*0.16)],fill=(60,185,60))
    # Maison
    if decor in("maison","danger"):
        mx,my,mw,mh=30,int(S*0.62),int(S*0.28),int(S*0.22)
        draw.rectangle([mx,my-mh,mx+mw,my],fill=P.WALL,outline=P.OUTLINE,width=2)
        draw.polygon([mx-10,my-mh,mx+mw//2,my-mh-int(S*0.09),mx+mw+10,my-mh],fill=P.ROOF,outline=P.OUTLINE,width=2)
        draw.rectangle([mx+mw//2-15,my-int(S*0.1),mx+mw//2+15,my],fill=P.DOOR,outline=P.OUTLINE,width=2)
        wl=P.WINDOW
        if mood=="dusk": wl=(255,255,180)
        for wx2 in[mx+8,mx+mw-38]:
            draw.rectangle([wx2,my-int(S*0.17),wx2+30,my-int(S*0.1)],fill=wl,outline=P.OUTLINE,width=2)
        if mood=="dusk":
            for fi in range(5):
                fh2=30+int(18*math.sin(frame*0.22+fi*0.8))
                fx2=mx+10+fi*int(mw/5)
                draw.ellipse([fx2-8,my-mh-fh2,fx2+8,my-mh],fill=P.FLAME_O)
                draw.ellipse([fx2-4,my-mh-fh2-8,fx2+4,my-mh-6],fill=P.FLAME_C)

def anim_off(action,frame):
    if action in("saute_joie","saute_promesse","salue_saute","fait_betise_saute"):
        return 0,-abs(int(30*math.sin(frame*0.16)))
    if action=="saute_peur":
        return int(4*math.sin(frame*0.45)),-abs(int(18*math.sin(frame*0.32)))
    if action in("court_vite","marche_content","court_panique"):
        return int(5*math.sin(frame*0.12)),int(5*math.sin(frame*0.22))
    if action=="pleure_assise": return 0,int(Config.SIZE*0.04)
    return 0,int(3*math.sin(frame*0.07))

def draw_char(draw,cx,cy,action,emotion,frame,genre):
    S=Config.SIZE
    dx,dy=anim_off(action,frame)
    x,y=cx+dx,cy+dy
    shirt=P.SHIRT_G if genre=="fille" else P.SHIRT_B
    hair=P.HAIR_G if genre=="fille" else P.HAIR_B
    eye_c=P.EYE_G if genre=="fille" else P.EYE_B
    # Ombre
    draw.ellipse([cx-int(S*0.06),cy+int(S*0.015),cx+int(S*0.06),cy+int(S*0.03)],fill=(0,0,0))
    # Corps
    if emotion=="triste": shirt=lc(shirt,(130,130,160),0.4)
    elif emotion=="effraye": shirt=lc(shirt,(180,180,190),0.35)
    draw.ellipse([x-int(S*0.05),y-int(S*0.04),x+int(S*0.05),y+int(S*0.075)],fill=shirt,outline=P.OUTLINE,width=2)
    # Jambes
    u=int(S*0.008)
    if action=="pleure_assise":
        draw.ellipse([x-int(S*0.06),y+int(S*0.07),x+int(S*0.01),y+int(S*0.13)],fill=P.PANTS,outline=P.OUTLINE,width=2)
        draw.ellipse([x+int(S*0.01),y+int(S*0.07),x+int(S*0.06),y+int(S*0.13)],fill=P.PANTS,outline=P.OUTLINE,width=2)
    else:
        sw=int(20*math.sin(frame*0.2)) if action in("court_vite","marche_content","court_panique") else 3
        draw.line([x-int(S*0.02),y+int(S*0.065),x-int(S*0.03)-sw,y+int(S*0.12)],fill=P.PANTS,width=int(S*0.022))
        draw.line([x+int(S*0.02),y+int(S*0.065),x+int(S*0.03)+sw,y+int(S*0.12)],fill=P.PANTS,width=int(S*0.022))
        draw.ellipse([x-int(S*0.05)-sw,y+int(S*0.11),x-int(S*0.01)-sw,y+int(S*0.135)],fill=P.SHOE,outline=P.OUTLINE,width=2)
        draw.ellipse([x+int(S*0.01)+sw,y+int(S*0.11),x+int(S*0.05)+sw,y+int(S*0.135)],fill=P.SHOE,outline=P.OUTLINE,width=2)
    # Bras
    skin=P.SKIN
    def arm(x1,y1,x2,y2):
        draw.line([x1,y1,x2,y2],fill=skin,width=int(S*0.018))
        draw.ellipse([x2-5,y2-5,x2+5,y2+5],fill=skin,outline=P.OUTLINE,width=1)
    sw2=int(22*math.sin(frame*0.18))
    if action=="saute_joie":
        arm(x-int(S*0.046),y-int(S*0.008),x-int(S*0.084),y-int(S*0.078))
        arm(x+int(S*0.046),y-int(S*0.008),x+int(S*0.084),y-int(S*0.078))
    elif action in("court_vite","marche_content","court_panique"):
        arm(x-int(S*0.046),y,x-int(S*0.07)+sw2,y+int(S*0.022))
        arm(x+int(S*0.046),y,x+int(S*0.07)-sw2,y+int(S*0.022))
    elif action=="appelle_gestes":
        gh=int(30*math.sin(frame*0.16))
        arm(x-int(S*0.046),y,x-int(S*0.09),y-int(S*0.062)-gh)
        arm(x+int(S*0.046),y,x+int(S*0.09),y-int(S*0.062)+gh)
    elif action=="saute_peur":
        t2=int(6*math.sin(frame*0.45))
        arm(x-int(S*0.046),y+t2,x-int(S*0.075),y-int(S*0.05)+t2)
        arm(x+int(S*0.046),y-t2,x+int(S*0.075),y-int(S*0.05)-t2)
    elif action=="pointe_enfant":
        arm(x-int(S*0.046),y,x-int(S*0.06),y+int(S*0.022))
        draw.line([x+int(S*0.046),y,x+int(S*0.1),y-int(S*0.02)],fill=skin,width=int(S*0.018))
        draw.ellipse([x+int(S*0.094),y-int(S*0.035),x+int(S*0.116),y-int(S*0.013)],fill=skin,outline=P.OUTLINE,width=1)
    elif action=="saute_promesse":
        arm(x-int(S*0.046),y,x-int(S*0.06),y+int(S*0.025))
        arm(x+int(S*0.046),y,x+int(S*0.08),y-int(S*0.086))
    elif action=="salue_saute":
        arm(x-int(S*0.046),y,x-int(S*0.06),y+int(S*0.025))
        bh=int(25*math.sin(frame*0.2))
        arm(x+int(S*0.046),y,x+int(S*0.094),y-int(S*0.05)+bh)
    elif action=="fait_betise_saute":
        arm(x-int(S*0.046),y,x-int(S*0.07),y-int(S*0.03))
        arm(x+int(S*0.046),y,x+int(S*0.086),y-int(S*0.04))
    elif action=="pleure_assise":
        arm(x-int(S*0.046),y+int(S*0.034),x-int(S*0.025),y+int(S*0.066))
        arm(x+int(S*0.046),y+int(S*0.034),x+int(S*0.025),y+int(S*0.066))
    elif action=="decouvre_surpris":
        arm(x+int(S*0.046),y,x+int(S*0.084),y+int(S*0.005))
        arm(x-int(S*0.046),y,x-int(S*0.06),y+int(S*0.025))
    elif action in("ecoute_hoche","hesite_balance"):
        arm(x-int(S*0.046),y,x-int(S*0.062),y+int(S*0.022))
        arm(x+int(S*0.046),y,x+int(S*0.062),y+int(S*0.022))
    else:
        arm(x-int(S*0.046),y,x-int(S*0.062),y+int(S*0.022))
        arm(x+int(S*0.046),y,x+int(S*0.062),y+int(S*0.022))
    # Tête
    hy=y-int(S*0.13)
    draw.ellipse([x-int(S*0.066),hy,x+int(S*0.066),hy+int(S*0.136)],fill=P.SKIN,outline=P.OUTLINE,width=2)
    # Cheveux
    draw.arc([x-int(S*0.064),hy,x+int(S*0.064),hy+int(S*0.07)],180,0,fill=hair,width=10)
    if genre=="fille":
        draw.rectangle([x-int(S*0.07),hy+int(S*0.012),x-int(S*0.042),hy+int(S*0.094)],fill=hair)
        draw.rectangle([x+int(S*0.042),hy+int(S*0.012),x+int(S*0.07),hy+int(S*0.094)],fill=hair)
    # Yeux
    ey=hy+int(S*0.054)
    ew,eh=14,12
    if emotion in("surpris","effraye"): eh=16
    elif emotion in("heureux","fier"): eh=10
    cligne=(frame%75)<3
    for side in(-1,1):
        ox=x+side*int(S*0.034)
        if cligne:
            draw.arc([ox-ew,ey-3,ox+ew,ey+5],0,180,fill=P.OUTLINE,width=2)
        else:
            draw.ellipse([ox-ew,ey-eh,ox+ew,ey+eh],fill=P.WHITE,outline=P.OUTLINE,width=2)
            draw.ellipse([ox-6,ey-5,ox+6,ey+5],fill=eye_c)
            draw.ellipse([ox-4,ey-3,ox+4,ey+3],fill=(8,8,18))
            draw.ellipse([ox-10,ey-8,ox-3,ey-2],fill=P.WHITE)
    # Joues
    draw.ellipse([x-int(S*0.076),ey+5,x-int(S*0.044),ey+20],fill=P.CHEEK)
    draw.ellipse([x+int(S*0.044),ey+5,x+int(S*0.076),ey+20],fill=P.CHEEK)
    # Bouche
    my2=hy+int(S*0.096)
    if emotion in("heureux","fier","determine"):
        draw.arc([x-10,my2-5,x+10,my2+8],0,180,fill=(185,65,65),width=3)
    elif emotion in("triste","desole"):
        draw.arc([x-10,my2+5,x+10,my2+14],180,0,fill=(178,65,65),width=3)
    elif emotion in("surpris","effraye"):
        draw.ellipse([x-9,my2-2,x+9,my2+14],fill=(135,48,48))
    else:
        draw.line([x-7,my2+6,x+7,my2+6],fill=(168,68,68),width=2)
    # FX larmes
    if emotion=="triste":
        for s2 in(-1,1):
            lx=x+s2*int(S*0.056); ly=ey+int(S*0.025)+int(5*math.sin(frame*0.22+s2))
            draw.polygon([lx-4,ly,lx+4,ly,lx,ly+14],fill=P.TEAR)
    # FX vitesse
    if action in("court_vite","court_panique"):
        for li in range(4):
            lx2=x-int(S*0.12)-li*10; ly2=y+li*6
            draw.line([lx2,ly2,lx2+int(S*0.044),ly2],fill=(160,165,190),width=2)


_FONTS = None
def get_fonts():
    global _FONTS
    if _FONTS: return _FONTS
    try:
        S=Config.SIZE
        _FONTS={
            "big":   ImageFont.truetype(Config.FONT_BOLD,   max(16,S//20)),
            "med":   ImageFont.truetype(Config.FONT_BOLD,   max(13,S//28)),
            "small": ImageFont.truetype(Config.FONT_REGULAR,max(12,S//32)),
        }
    except:
        d=ImageFont.load_default()
        _FONTS={"big":d,"med":d,"small":d}
    return _FONTS

def song_line(song,part):
    text=getattr(song,part,"")
    for sep in["...","!","."]:
        idx=text.find(sep)
        if idx>15: return text[:idx].strip()
    return text[:48].strip()

def draw_ui(img,scene,f_in_scene,song,genre):
    draw=ImageDraw.Draw(img)
    F=get_fonts(); S=Config.SIZE
    # Bandeau haut
    overlay=Image.new("RGBA",(S,50),(0,0,0,0))
    d2=ImageDraw.Draw(overlay)
    for yy in range(50):
        alpha=int(210*(1-yy/50))
        d2.line([(0,yy),(S,yy)],fill=(*P.UI_BG,alpha))
    img.paste(Image.alpha_composite(img.crop((0,0,S,50)).convert("RGBA"),overlay),(0,0))
    draw=ImageDraw.Draw(img)
    draw.text((12,8),scene.titre[:40],fill=P.UI_TFG,font=F["med"])
    # Bandeau bas
    bh=int(S*0.22)
    overlay2=Image.new("RGBA",(S,bh),(0,0,0,0))
    d3=ImageDraw.Draw(overlay2)
    for yy in range(bh):
        alpha=int(230*(yy/bh)**0.4)
        d3.line([(0,yy),(S,yy)],fill=(*P.SONG_BG,alpha))
    img.paste(Image.alpha_composite(img.crop((0,S-bh,S,S)).convert("RGBA"),overlay2),(0,S-bh))
    draw=ImageDraw.Draw(img)
    sl=song_line(song,scene.song_part)
    if sl:
        disp=sl[:40]+"…" if len(sl)>42 else sl
        draw.text((12,S-bh+8),f"♪ {disp}",fill=P.SONG_FG,font=F["small"])
    draw.line([(12,S-bh+32),(S-12,S-bh+32)],fill=(80,60,140),width=1)
    dlg=scene.dialogue[:40]+"…" if len(scene.dialogue)>42 else scene.dialogue
    draw.text((12,S-bh+38),f"» {dlg}",fill=P.UI_DFG,font=F["small"])
    # Barre progression
    prog=f_in_scene/max(1,scene.duree)
    bw=S-24
    draw.rounded_rectangle([12,S-14,S-12,S-4],radius=4,fill=(50,50,90))
    fill_w=int(bw*prog)+12
    if fill_w>22:
        draw.rounded_rectangle([12,S-14,fill_w,S-4],radius=4,fill=P.UI_BAR)


def easing(t): return 3*t**2-2*t**3

def blend(f1,f2,t):
    return np.clip(f1*(1-t)+f2*t,0,255).astype(np.uint8)

def render_scene(scene,genre,song,gframe):
    frames=[]
    for f in range(scene.duree):
        img=Image.new("RGBA",(Config.SIZE,Config.SIZE))
        draw=ImageDraw.Draw(img)
        draw_bg(draw,scene.decor,scene.sky_mood,gframe+f)
        draw_char(draw,Config.SIZE//2,int(Config.SIZE*0.58),
                  scene.action,scene.emotion,gframe+f,genre)
        draw_ui(img,scene,f,song,genre)
        bgr=cv2.cvtColor(np.array(img.convert("RGB")),cv2.COLOR_RGB2BGR)
        frames.append(bgr)
    return frames

def render_all(scenes,genre,song,progress_bar):
    all_frames=[]; gframe=0
    EF=Config.EASE_FRAMES
    total=len(scenes)
    for i,scene in enumerate(scenes):
        progress_bar.progress((i)/total,text=f"Rendu scène {i+1}/{total} — {scene.acte_label}")
        sf=render_scene(scene,genre,song,gframe)
        if all_frames and EF>0:
            prev=all_frames[-EF:]
            nxt=sf[:EF]
            bl=[blend(prev[j],nxt[j],easing(j/EF)) for j in range(min(EF,len(prev),len(nxt)))]
            all_frames[-len(bl):]=bl
        all_frames.extend(sf)
        gframe+=scene.duree
    progress_bar.progress(1.0,text="Rendu terminé !")
    return all_frames


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO
# ══════════════════════════════════════════════════════════════════════════════
async def _edge_gen(text,voice,rate,pitch,out):
    communicate=edge_tts.Communicate(text=text,voice=voice,rate=rate,pitch=pitch)
    await communicate.save(out)

def gen_audio(char,song,folder,status_text):
    sections=[
        song.intro,"...",song.acte1,"...",song.acte2,"...",
        song.refrain1,"...",song.acte3,"...",song.acte4,"...",
        song.refrain2,"...",song.acte5,"...",song.acte6,"...",
        song.outro,"...",song.refrain2,
    ]
    full_text="  ".join(sections)
    voice=Config.VOICE_FILLE if char.genre=="fille" else Config.VOICE_GARCON
    vpath=os.path.join(folder,"voix.mp3")
    ok=False
    if _EDGE_TTS_OK:
        try:
            status_text.text("Génération voix neurale...")
            asyncio.run(_edge_gen(full_text,voice,Config.VOICE_RATE,Config.VOICE_PITCH,vpath))
            ok=True
        except Exception as e:
            st.warning(f"edge-tts: {e} → fallback gTTS")
    if not ok:
        status_text.text("Génération voix (gTTS)...")
        gTTS(text=full_text,lang="fr",slow=True).save(vpath)
    return vpath

def encode_video(frames,audio_path,folder,prenom):
    silent=os.path.join(folder,"_silent.mp4")
    final=os.path.join(folder,f"ANIME_{prenom.upper()}.mp4")
    h,w=frames[0].shape[:2]
    writer=cv2.VideoWriter(silent,cv2.VideoWriter_fourcc(*"mp4v"),Config.FPS,(w,h))
    for frame in frames:
        writer.write(frame)
    writer.release()
    result=subprocess.run([
        "ffmpeg","-y","-i",silent,"-i",audio_path,
        "-c:v","libx264","-preset","fast","-crf",str(Config.CRF),
        "-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest",final,
    ],capture_output=True,text=True)
    if os.path.exists(silent): os.remove(silent)
    return final


# ══════════════════════════════════════════════════════════════════════════════
#  INTERFACE STREAMLIT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="Studio Animé Éducatif",
        page_icon="🎬",
        layout="centered"
    )

    st.title("🎬 Studio Animé Éducatif")
    st.markdown("*Écris la bêtise de ton enfant → une vidéo animée éducative est générée automatiquement.*")

    # ── Clé API dans la sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input(
            "Clé API Anthropic",
            type="password",
            placeholder="sk-ant-...",
            help="Obtiens ta clé sur console.anthropic.com"
        )
        st.markdown("---")
        st.caption("💡 La clé n'est jamais sauvegardée.")
        st.caption("📖 [Obtenir une clé API](https://console.anthropic.com)")

    # ── Zone principale ───────────────────────────────────────────────────────
    col1, col2 = st.columns([3,1])
    with col1:
        probleme = st.text_area(
            "La bêtise de ton enfant",
            placeholder="Ex: Mon fils Adam, 5 ans, touche les prises électriques avec ses doigts",
            height=100,
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Exemples rapides :**")
        if st.button("⚡ Prises"):
            st.session_state["ex"] = "Mon fils Adam, 5 ans, touche les prises électriques"
        if st.button("🔪 Couteaux"):
            st.session_state["ex"] = "Mon fils Youssef, 7 ans, joue avec les couteaux de cuisine"
        if st.button("💊 Médicaments"):
            st.session_state["ex"] = "Ma fille Inès, 6 ans, mange des médicaments dans l'armoire"
        if st.button("🏊 Piscine"):
            st.session_state["ex"] = "Ma fille Lina, 4 ans, s'approche seule du bord de la piscine"

    if "ex" in st.session_state:
        probleme = st.session_state.pop("ex")
        st.rerun()

    # ── Bouton générer ────────────────────────────────────────────────────────
    if st.button("🎬 Générer la vidéo", type="primary", use_container_width=True):
        if not api_key:
            st.error("Entre ta clé API Anthropic dans la barre latérale (⚙️).")
            st.stop()
        if not probleme.strip():
            st.error("Écris la bêtise de ton enfant avant de générer.")
            st.stop()

        with st.status("Génération en cours...", expanded=True) as status:

            # 1. IA génère le scénario
            st.write("🤖 Claude génère le scénario personnalisé...")
            try:
                char, song, danger = generate_with_ai(probleme, api_key)
            except Exception as e:
                st.error(f"Erreur API : {e}")
                st.stop()

            st.write(f"✅ Personnage : **{char.prenom}**, {char.age} ans ({char.genre})")
            st.write(f"🎵 Chanson : *{song.titre}*")

            # 2. Afficher la chanson
            with st.expander("📜 Voir la chanson générée", expanded=False):
                parts=[
                    ("🎵 Intro", song.intro),
                    ("Acte 1 — Vie normale", song.acte1),
                    ("Acte 2 — La tentation", song.acte2),
                    ("🚨 Refrain 1", song.refrain1),
                    ("⚠️ Acte 3 — La bêtise", song.acte3),
                    ("🔥 Acte 4 — Conséquence", song.acte4),
                    ("💡 Refrain 2", song.refrain2),
                    ("😢 Acte 5 — Compréhension", song.acte5),
                    ("🤝 Acte 6 — La promesse", song.acte6),
                    ("🫵 Outro", song.outro),
                ]
                for label,text in parts:
                    st.markdown(f"**{label}**")
                    st.caption(text)

            # 3. Rendu vidéo
            st.write("🎨 Rendu vidéo frame par frame...")
            scenes=build_scenes(char,song)
            progress=st.progress(0,"Démarrage du rendu...")
            frames=render_all(scenes,char.genre,song,progress)

            # 4. Audio
            st.write("🎙️ Génération audio...")
            with tempfile.TemporaryDirectory() as tmpdir:
                status_text=st.empty()
                audio_path=gen_audio(char,song,tmpdir,status_text)
                status_text.empty()

                # 5. Encodage
                st.write("⚙️ Encodage vidéo finale...")
                final_path=encode_video(frames,audio_path,tmpdir,char.prenom)

                if not os.path.exists(final_path):
                    st.error("Erreur lors de l'encodage. Vérifie que ffmpeg est installé.")
                    st.stop()

                # 6. Lecture + téléchargement
                with open(final_path,"rb") as f:
                    video_bytes=f.read()

            status.update(label="✅ Vidéo générée avec succès !", state="complete")

        st.success(f"🎉 Vidéo prête pour **{char.prenom}** !")
        st.video(video_bytes)
        st.download_button(
            label="💾 Télécharger la vidéo MP4",
            data=video_bytes,
            file_name=f"anime_{char.prenom.lower()}_{danger.replace(' ','_')}.mp4",
            mime="video/mp4",
            use_container_width=True,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption("Studio Animé Éducatif · Powered by Claude AI · Bienveillant et éducatif pour les enfants de 3 à 8 ans")


if __name__ == "__main__":
    main()
