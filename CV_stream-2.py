#!/usr/bin/env python
# coding: utf-8

import os
from dotenv import load_dotenv
load_dotenv()  # charge .env si présent

import openai
import streamlit as st
import requests
import io
from pathlib import Path

# --- 0. Configuration de la page et du template LaTeX ---
st.set_page_config(page_title="Générateur de CV PDF", layout="centered")
st.title("🧠 Générateur de CV")

SCRIPT_DIR    = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR / "template.tex"

# --- 1. Configuration de l'API OpenAI ---
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    key_input = st.text_input(
        label="Entrez votre clé API OpenAI", 
        type="password",
        help="Vous pouvez créer un fichier .env ou exporter la variable OPENAI_API_KEY"
    )
    if key_input:
        openai.api_key = key_input
    else:
        st.error(
            "Clé API OpenAI introuvable. \n"
            "Définissez OPENAI_API_KEY dans votre environnement ou entrez-la ci-dessus."
        )
        st.stop()

# --- 1.1. Prompt système dédié pour une qualité "CV Finance" ---
SYSTEM_PROMPT = (
    "Vous êtes un rédacteur professionnel de CV, spécialisé dans la finance.\n"
    "En fonction du champ à traiter, adaptez votre sortie :\n"
    "• Titres de poste ou de projet (exp_title, project_title) :\n"
    "  – Proposez un intitulé court, formel et impactant (3–6 mots).\n"
    "• Descriptions d’expérience ou de projet (exp_item*, project_item*) :\n"
    "  – Générez un bullet point orienté action, au passé, quantifié si possible, "
    "avec un verbe d’action (Optimized, Forecasted, Automated, …).\n"
    "• Compétences (skills_*) :\n"
    "  – Listez des mots-clés techniques ou métiers, séparés par des virgules, "
    "en phase avec un CV financier.\n"
    "Le texte original se trouve dans le message utilisateur.\n"
    "Répondez uniquement avec la version reformulée, sans puce ni numéro."
)

# --- 2. Exemple de données pour préremplir le formulaire ---
example_data = {
    # ... (tes données d’exemple restent inchangées) ...
}

def load_example(field_key):
    st.session_state[field_key] = example_data[field_key]

# --- 3. Fonction de reformulation via GPT ---
def reformuler_texte(texte: str) -> str:
    if not texte:
        return ""
    resp = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": texte}
        ],
        temperature=0.7,
        max_tokens=len(texte.split()) * 2
    )
    return resp.choices[0].message.content.strip()

def ameliorer_champ(field_key):
    brut = st.session_state[field_key]
    try:
        reform = reformuler_texte(brut)
        if reform:
            st.session_state[field_key] = reform
    except openai.error.PermissionError:
        st.error("PermissionError : vérifiez votre plan et votre moyen de paiement.")
    except openai.error.RateLimitError:
        st.error("Quota insuffisant : ajoutez un moyen de paiement ou augmentez votre quota.")
    except Exception as e:
        st.error(f"Erreur API GPT : {e}")
        st.stop()

# --- 5. Initialisation de session_state pour tous les champs ---
for key in example_data:
    st.session_state.setdefault(key, "")

# --- 6. Formulaire de saisie ---
st.header("1. Remplis ton CV")
fields = [
    # ... (liste des tuples key/label inchangée) ...
]
for key, label in fields:
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        st.text_input(label, key=key)
    with c2:
        st.button("Exemple", key=f"ex_{key}", on_click=load_example, args=(key,))
    with c3:
        st.button("GPT+", key=f"gpt_{key}", on_click=ameliorer_champ, args=(key,))

# --- 7. Génération du PDF via latexonline.cc ---
st.header("2. Génère ton PDF")
if st.button("📄 Générer mon CV"):
    if not TEMPLATE_PATH.exists():
        st.error(f"❌ template.tex introuvable : {TEMPLATE_PATH}")
        st.stop()

    # Remplissage du template .tex
    tex = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key in example_data:
        tex = tex.replace(f"{{{{{key}}}}}", st.session_state[key])

    # Appel au service de compilation en ligne
    files = {"file": ("cv.tex", tex.encode("utf-8"))}
    resp = requests.post("https://latexonline.cc/compile", files=files)
    if resp.status_code != 200:
        st.error(f"❌ La compilation a échoué (status {resp.status_code})")
        st.stop()

    # Téléchargement du PDF
    pdf_bytes = resp.content
    st.success("✅ CV compilé avec succès !")
    st.download_button(
        "⬇️ Télécharger le PDF",
        data=pdf_bytes,
        file_name="cv.pdf",
        mime="application/pdf"
    )
