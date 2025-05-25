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

# ✅ Chargement des données avec les bons noms de fichiers
resistance_df = pd.read_csv("resistance_data.csv")
pheno_df = pd.read_csv("phenotypes.csv")
advanced_df = pd.read_csv("advanced_data.csv")
weekly_df = pd.read_excel("staph_aureus_hebdomadaire.xlsx")

# 📊 Fonction de détection d'alarmes (méthode de Tukey)
def detect_outliers_tukey(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return series > (q3 + 1.5 * iqr)

# ---------------------- VUE D'ENSEMBLE -----------------------
if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")
    col1, col2, col3 = st.columns(3)
    col1.metric("% MRSA", "23%", "+2%")
    col2.metric("% MSSA", "77%", "-2%")
    col3.metric("Année critique", "2024")

    st.subheader("Évolution temporelle")
    if 'Année' in resistance_df.columns:
        trend = resistance_df.groupby(["Année", "Phénotype"])["Taux de résistance (%)"].mean().reset_index()
        fig = px.line(trend, x="Année", y="Taux de résistance (%)", color="Phénotype")
        st.plotly_chart(fig)
    else:
        st.warning("Colonne 'Année' manquante dans resistance_data.csv")

# ------------------ RÉSISTANCE AUX ANTIBIOTIQUES -------------------
elif page == "Résistance aux antibiotiques":
    st.title("Résistance aux antibiotiques")
    if "Antibiotique" in resistance_df.columns:
        ab = st.selectbox("Choisir un antibiotique", resistance_df["Antibiotique"].unique())
        df_ab = resistance_df[resistance_df["Antibiotique"] == ab]
        df_ab["Alarme"] = detect_outliers_tukey(df_ab["Taux de résistance (%)"])
        fig = px.bar(df_ab, x="Année", y="Taux de résistance (%)", color="Alarme",
                     color_discrete_map={True: "darkred", False: "steelblue"},
                     title=f"Résistance à {ab}")
        st.plotly_chart(fig)
    else:
        st.warning("Colonne 'Antibiotique' absente du fichier.")

# --------------------- PHÉNOTYPES -----------------------
elif page == "Phénotypes de résistance":
    st.title("Phénotypes de résistance")
    if "Phénotype" in pheno_df.columns:
        fig = px.pie(pheno_df, names="Phénotype", values="Nombre", title="Répartition des phénotypes")
        st.plotly_chart(fig)
        st.subheader("Détection d'alertes")
        pheno_df["Alarme"] = detect_outliers_tukey(pheno_df["Nombre"])
        st.dataframe(pheno_df[pheno_df["Alarme"]])
    else:
        st.warning("Colonnes 'Phénotype' et 'Nombre' manquantes.")

# --------------------- ANALYSE AVANCÉE ----------------------
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

# ----------------------- DOCUMENTATION -----------------------
elif page == "Documentation":
    st.title("Documentation")
    st.markdown("""
    ### Sources de données
    - Données hospitalières anonymisées
    - Microbiologie (résultats antibiogrammes)

    ### Règle des alarmes
    Une alerte est déclenchée si une valeur dépasse Q3 + 1.5 x IQR (règle de Tukey).

    ### Navigation
    - Vue d'ensemble : résumé global
    - Résistance : sélection par antibiotique
    - Phénotypes : camembert MRSA/MSSA
    - Analyse avancée : âge/sexe/service
    """)

# ----------------- ANALYSE HEBDOMADAIRE -------------------
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
