import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Surveillance S. aureus", layout="wide")
st.sidebar.title("🧪 Tableau de bord S. aureus")

page = st.sidebar.radio("Aller à", [
    "1. Vue d'ensemble",
    "2. Résistance aux antibiotiques",
    "3. Phénotypes de résistance",
    "4. Analyse avancée",
    "5. Documentation",
    "6. Analyse hebdomadaire"
])

# Chargement des données (adaptés aux fichiers fournis)
resistance_df = pd.read_csv("resistance_data.csv")
pheno_df = pd.read_excel("staph_aureus_pheno_final.xlsx")
advanced_df = pd.read_excel("staph_aureus_percentages_avec_alertes.xlsx")
weekly_df = pd.read_excel("staph aureus hebdomadaire excel.xlsx")

# Détection des alarmes

def detect_outliers_tukey(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    return series > upper

# PAGE 1
if page == "1. Vue d'ensemble":
    st.title("Vue d'ensemble")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("% MRSA", "23%", "+2%")
    with col2:
        st.metric("% MSSA", "77%", "-2%")
    with col3:
        st.metric("Année critique", "2022")
    st.subheader("Évolution temporelle")
    if 'Année' in resistance_df.columns:
        trend_data = resistance_df.groupby(["Année", "Phénotype"])["Taux de résistance (%)"].mean().reset_index()
        fig = px.line(trend_data, x="Année", y="Taux de résistance (%)", color="Phénotype")
        st.plotly_chart(fig)
    else:
        st.warning("Les colonnes attendues ne sont pas présentes dans le fichier de données.")

# PAGE 2
elif page == "2. Résistance aux antibiotiques":
    st.title("Résistance aux antibiotiques")
    if "Antibiotique" in resistance_df.columns:
        ab = st.selectbox("Antibiotique", resistance_df["Antibiotique"].unique())
        df_ab = resistance_df[resistance_df["Antibiotique"] == ab]
        df_ab["Alarme"] = detect_outliers_tukey(df_ab["Taux de résistance (%)"])
        fig = px.bar(df_ab, x="Année", y="Taux de résistance (%)", color="Alarme", 
                     color_discrete_map={True: "darkred", False: "steelblue"}, title=f"Taux de résistance - {ab}")
        st.plotly_chart(fig)
    else:
        st.warning("Colonne 'Antibiotique' manquante dans les données.")

# PAGE 3
elif page == "3. Phénotypes de résistance":
    st.title("Phénotypes")
    if "Phénotype" in pheno_df.columns:
        fig = px.pie(pheno_df, names="Phénotype", values="Nombre", title="Proportions")
        st.plotly_chart(fig)
        st.subheader("Alarmes phénotypiques")
        pheno_df["Alarme"] = detect_outliers_tukey(pheno_df["Nombre"])
        st.dataframe(pheno_df[pheno_df["Alarme"]])
    else:
        st.warning("Colonnes 'Phénotype' ou 'Nombre' absentes.")

# PAGE 4
elif page == "4. Analyse avancée":
    st.title("Analyse avancée")
    if "Age" in advanced_df.columns:
        age = st.slider("Filtrer par âge", 0, 100, (0, 100))
        sexe = st.selectbox("Sexe", ["Tous", "Homme", "Femme"])
        filt = advanced_df[(advanced_df["Age"] >= age[0]) & (advanced_df["Age"] <= age[1])]
        if sexe != "Tous":
            filt = filt[filt["Sexe"] == sexe]
        st.dataframe(filt)
        st.download_button("Télécharger", filt.to_csv(index=False), "filtre.csv")
    else:
        st.warning("Colonnes 'Age' et 'Sexe' manquantes dans le fichier.")

# PAGE 5
elif page == "5. Documentation":
    st.title("Documentation")
    st.markdown("""
    ### Sources
    - Données hospitalières anonymisées
    - Microbiologie locale
    ### Alarme
    - Basée sur la méthode de Tukey (Q3 + 1.5 * IQR)
    ### Navigation
    - Vue globale, antibiotiques, phénotypes, filtrage clinique
    """)

# PAGE 6
elif page == "6. Analyse hebdomadaire":
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
        st.error(f"🔴 Alerte sur: {', '.join(alertes)}")
        st.dataframe(df_filtre[df_filtre[alertes].isin(["R"]).any(axis=1)][["IPP_PASTEL"] + alertes])
    else:
        st.success("✅ Aucun seuil d'alerte dépassé cette semaine pour ce service.")
