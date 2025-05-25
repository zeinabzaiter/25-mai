import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Surveillance S. aureus", layout="wide")
st.sidebar.title("🧪 Tableau de bord S. aureus")

page = st.sidebar.radio("Aller à", [
    "Vue d'ensemble",
    "Résistance aux antibiotiques",
    "Phénotypes de résistance",
    "Analyse avancée",
    "Documentation",
    "Analyse hebdomadaire"
])

# Chargement des données
resistance_df = pd.read_csv("resistance_data.csv")
pheno_df = pd.read_csv("phenotypes.csv")
advanced_df = pd.read_csv("advanced_data.csv")
weekly_df = pd.read_excel("staph_aureus_hebdomadaire.xlsx")
pheno_pct = pd.read_csv("phenotypes_percentages_weekly.csv")

# Fonction pour détecter les valeurs aberrantes (règle de Tukey)
def detect_outliers_tukey(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return series > (q3 + 1.5 * iqr)

# PAGE 1 - Vue d'ensemble
if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")

    moyennes = pheno_pct[["MRSA", "VRSA", "Other", "Wild"]].mean().round(1)

    col1, col2, col3 = st.columns(3)
    col1.metric("% MRSA", f"{moyennes['MRSA']}%")
    col2.metric("% VRSA", f"{moyennes['VRSA']}%")
    col3.metric("% Other", f"{moyennes['Other']}%")

    col4, _ = st.columns([1, 2])
    col4.metric("% Wild", f"{moyennes['Wild']}%")

    st.subheader("Évolution temporelle")
    st.info("À personnaliser si des données temporelles sont disponibles.")

# Le reste des pages reste inchangé... (à compléter selon les besoins)

# À compléter : autres pages comme dans la version précédente (antibiotiques, phénotypes, etc.)
elif page == "Analyse avancée":
    st.title("Analyse avancée")
    if "Age" in advanced_df.columns and "Sexe" in advanced_df.columns:
        age = st.slider("Âge", 0, 100, (0, 100))
        sexe = st.selectbox("Sexe", ["Tous", "Homme", "Femme"])
        filt = advanced_df[(advanced_df["Age"] >= age[0]) & (advanced_df["Age"] <= age[1])]
        if sexe != "Tous":
            filt = filt[filt["Sexe"] == sexe]
        st.dataframe(filt)
        st.download_button("Télécharger les données filtrées", filt.to_csv(index=False), "filtre.csv")
    else:
        st.warning("Colonnes 'Age' ou 'Sexe' manquantes.")
elif page == "Documentation":
    st.title("Documentation")
    st.markdown("""
    ### Sources de données
    - Données hospitalières anonymisées
    - Résultats microbiologiques

    ### Méthodologie
    - Alerte : Règle de Tukey (Q3 + 1.5 * IQR)
    - Agrégation hebdomadaire et annuelle

    ### Navigation
    - Vue d'ensemble : synthèse globale
    - Résistance : par antibiotique
    - Phénotypes : typologie MRSA, VRSA...
    """)
elif page == "Analyse hebdomadaire":
    st.title("Analyse hebdomadaire avec alarmes")
    weekly_df["DATE_PRELEVEMENT"] = pd.to_datetime(weekly_df["DATE_PRELEVEMENT"], errors="coerce")
    weekly_df["Semaine"] = weekly_df["DATE_PRELEVEMENT"].dt.isocalendar().week

    semaine = st.selectbox("Semaine", sorted(weekly_df["Semaine"].dropna().unique()))
    service = st.selectbox("Service", sorted(weekly_df["LIBELLE_DEMANDEUR"].dropna().unique()))
    df_filtre = weekly_df[(weekly_df["Semaine"] == semaine) & (weekly_df["LIBELLE_DEMANDEUR"] == service)]

    antibiotiques = [col for col in df_filtre.columns if col in [
        "Vancomycine", "Teicoplanine", "Gentamycine", "Oxacilline", "Daptomycine",
        "Dalbavancine", "Clindamycine", "Cotrimoxazole", "Linezolide"]]

    alertes = []
    for ab in antibiotiques:
        if ab in df_filtre.columns:
            counts = df_filtre[ab].value_counts()
            if "R" in counts and counts["R"] > df_filtre.shape[0] * 0.25:
                alertes.append(ab)

    if alertes:
        st.error(f"🔴 Alerte sur : {', '.join(alertes)}")
        st.dataframe(df_filtre[df_filtre[alertes].isin(["R"]).any(axis=1)][["IPP_PASTEL"] + alertes])
    else:
        st.success("✅ Aucun seuil d'alerte dépassé cette semaine pour ce service.")
