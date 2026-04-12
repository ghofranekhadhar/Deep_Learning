# 🎬 Studio Animé Éducatif — Streamlit

Application complète : le parent écrit la bêtise de son enfant → Claude IA génère le scénario → vidéo animée MP4 créée automatiquement.

---

## 🚀 Déploiement sur Streamlit Cloud (GRATUIT)

### Étape 1 — Mettre le code sur GitHub
1. Crée un compte sur [github.com](https://github.com) si tu n'en as pas
2. Crée un nouveau dépôt (repository) — ex: `anime-educatif`
3. Upload ces 2 fichiers dans le dépôt :
   - `app.py`
   - `requirements.txt`

### Étape 2 — Déployer sur Streamlit Cloud
1. Va sur [share.streamlit.io](https://share.streamlit.io)
2. Connecte ton compte GitHub
3. Clique **New app**
4. Sélectionne ton dépôt `anime-educatif`
5. Fichier principal : `app.py`
6. Clique **Deploy** → l'app est en ligne en ~3 minutes !

### Étape 3 — Utiliser l'app
1. Ouvre le lien Streamlit donné (ex: `ton-app.streamlit.app`)
2. Dans la barre latérale ⚙️, entre ta clé API Anthropic
3. Écris la bêtise de l'enfant
4. Clique **Générer la vidéo**
5. La vidéo est prête en ~2-3 minutes, télécharge-la !

---

## 💻 Lancer en local (sur ton PC)

```bash
# Installe les dépendances
pip install -r requirements.txt

# Lance l'app
streamlit run app.py
```
Ouvre http://localhost:8501 dans ton navigateur.

---

## ⚠️ Notes importantes

- **ffmpeg** doit être installé sur la machine (Streamlit Cloud l'installe auto via `packages.txt`)
- La génération vidéo prend 2-4 minutes selon la longueur
- Les vidéos font ~15-30 Mo

## 📦 Fichier packages.txt (pour Streamlit Cloud)
Crée un fichier `packages.txt` dans ton dépôt GitHub avec :
```
ffmpeg
```
Cela installe ffmpeg automatiquement sur Streamlit Cloud.

---

## 🎯 Structure du projet
```
anime-educatif/
├── app.py           ← Application principale
├── requirements.txt ← Dépendances Python
└── packages.txt     ← Paquets système (ffmpeg)
```
