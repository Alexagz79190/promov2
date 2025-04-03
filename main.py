# main.py

import streamlit as st
from datetime import datetime, time as dt_time
from logic import charger_donnees, appliquer_exclusions, calculer_prix_promo
from utils import to_excel, update_status, load_file

st.set_page_config(page_title="Calculateur de Prix Promo", layout="centered")

st.title("Calculateur de Prix Promo")
log_container = st.empty()

# Upload des fichiers
st.subheader("Chargement des fichiers")
produit_file = load_file("export produit")
exclusion_file = load_file("exclusion produit")
remise_file = load_file("remise")

st.info("Champs requis dans le fichier **export produit** :\n- Identifiant produit\n- Fournisseur : identifiant\n- Famille : identifiant\n- Marque : identifiant\n- Code produit\n- Prix de vente en cours\n- Prix d'achat avec option\n- Prix de revient")

# Dates
st.subheader("Dates promo")
start_date = st.date_input("Date début", value=datetime.now().date())
start_time = st.time_input("Heure début", value=dt_time(0, 0))
end_date = st.date_input("Date fin", value=datetime.now().date())
end_time = st.time_input("Heure fin", value=dt_time(23, 59))
start_datetime = datetime.combine(start_date, start_time)
end_datetime = datetime.combine(end_date, end_time)

# Option de calcul
st.subheader("Options")
price_option = st.radio("Colonne de base pour le calcul :", ["Prix d'achat avec option", "Prix de revient"])

if st.button("Démarrer le calcul"):
    try:
        if not all([produit_file, exclusion_file, remise_file]):
            st.error("Tous les fichiers doivent être chargés.")
            update_status("Erreur : fichiers manquants.", log_container)
        else:
            update_status("Chargement des données...", log_container)
            data, exclusions, remises = charger_donnees(produit_file, exclusion_file, remise_file)

            update_status("Application des exclusions...", log_container)
            data_processed, data_excluded = appliquer_exclusions(data, exclusions)

            update_status("Calcul des prix promotionnels...", log_container)
            result_df, margin_issues_df, exclusion_from_calc_df = calculer_prix_promo(
                data_processed, remises, price_option, start_datetime, end_datetime
            )

            # Fusion des exclusions
            excl_final_df = data_excluded[['Code produit', 'Prix de vente en cours', "Prix d'achat avec option", "Prix de revient", "Exclusion Reason"]].copy()
            excl_final_df.rename(columns={"Exclusion Reason": "Raison exclusion"}, inplace=True)
            excl_final_df["Remise appliquée"] = ""
            excl_final_df["Raison de la remise"] = ""
            exclusion_total = pd.concat([excl_final_df, exclusion_from_calc_df], ignore_index=True)

            # Téléchargements
            st.download_button("📄 Télécharger les prix promo",
                               data=result_df.to_csv(index=False, sep=";", encoding="utf-8"),
                               file_name="prix_promo_output.csv")
            st.download_button("⚠️ Produits à marge anormale",
                               data=to_excel(margin_issues_df),
                               file_name="produits_avec_problemes_de_marge.xlsx")
            st.download_button("🚫 Produits exclus",
                               data=to_excel(exclusion_total),
                               file_name="produits_exclus.xlsx")

            update_status("✅ Calcul terminé et fichiers prêts.", log_container)
    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")
        update_status(f"Erreur critique : {e}", log_container)
