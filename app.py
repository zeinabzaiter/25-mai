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
# Chargement des autres antibiotiques
other_ab_df = pd.read_excel("other Antibiotiques staph aureus.xlsx")


# Fonction pour détecter les valeurs aberrantes (règle de Tukey)
def detect_outliers_tukey(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return series > (q3 + 1.5 * iqr)

# PAGE 1 - Vue d'ensemble
if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")

    if all(x in pheno_pct.columns for x in ["MRSA", "VRSA", "Other", "Wild"]):
        moyennes = pheno_pct[["MRSA", "VRSA", "Other", "Wild"]].mean().round(1)

        col1, col2, col3 = st.columns(3)
        col1.metric("% MRSA", f"{moyennes['MRSA']}%")
        col2.metric("% VRSA", f"{moyennes['VRSA']}%")
        col3.metric("% Other", f"{moyennes['Other']}%")

        col4, _ = st.columns([1, 2])
        col4.metric("% Wild", f"{moyennes['Wild']}%")

        st.subheader("Évolution temporelle")
        fig = px.line(pheno_pct, x="week", y=["MRSA", "VRSA", "Other", "Wild"], markers=True)
        fig.update_layout(title="Tendance hebdomadaire des phénotypes")
        st.plotly_chart(fig)
    else:
        st.info("À personnaliser si des données temporelles sont disponibles.")

# PAGE 2 - Résistance aux antibiotiques
elif page == "Résistance aux antibiotiques":
    st.title("Résistance aux antibiotiques")
    ab_columns = list(resistance_df.columns[resistance_df.columns.str.startswith(('%R', '% R'))]) + \
             list(other_ab_df.columns[other_ab_df.columns.str.startswith(('%R', '% R'))])

    if ab_columns:
        selected_ab = st.selectbox("Choisir un antibiotique", ab_columns)
        if selected_ab in resistance_df.columns:
    df_ab = resistance_df[["Semaine", selected_ab]].copy()
else:
    df_ab = other_ab_df[["Semaine", selected_ab]].copy()

        df_ab["Alarme"] = detect_outliers_tukey(df_ab[selected_ab])
        fig = px.bar(df_ab, x="Semaine", y=selected_ab, color="Alarme",
                     color_discrete_map={True: "darkred", False: "steelblue"},
                     title=f"Résistance à {selected_ab}")
        st.plotly_chart(fig)
    else:
        st.warning("Aucune colonne d'antibiotique trouvée.")

# PAGE 3 - Phénotypes de résistance
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

# PAGE 4 - Analyse avancée
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

# PAGE 5 - Documentation
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

# PAGE 6 - Analyse hebdomadaire
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
