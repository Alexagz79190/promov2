# logic.py

import pandas as pd
from itertools import product
from datetime import datetime


def charger_donnees(produit_file, exclusion_file, remise_file):
    data = pd.read_excel(produit_file, sheet_name='Worksheet')
    exclusions = pd.ExcelFile(exclusion_file)
    remises = pd.read_excel(remise_file)
    return data, exclusions, remises


def appliquer_exclusions(data: pd.DataFrame, exclusions: pd.ExcelFile):
    excl_code_agz = exclusions.parse('Code AGZ')['Code AGZ'].dropna().astype(str).tolist()
    excl_fournisseur = exclusions.parse('Founisseur ')['Identifiant fournisseur seul'].dropna().astype(int).tolist()
    excl_marque = exclusions.parse('Marque')['Identifiant marque seul'].dropna().astype(int).tolist()
    excl_fournisseur_famille = exclusions.parse('Fournisseur famille')[['Identifiant fournisseur', 'Identifiant famille']]

    all_combinations = list(product(
        excl_fournisseur_famille['Identifiant fournisseur'].unique(),
        excl_fournisseur_famille['Identifiant famille'].unique()
    ))
    combi_df = pd.DataFrame(all_combinations, columns=['Identifiant fournisseur', 'Identifiant famille'])

    data['Exclusion Reason'] = None
    data.loc[data['Code produit'].astype(str).isin(excl_code_agz), 'Exclusion Reason'] = 'Exclus: Code AGZ'
    data.loc[data['Fournisseur : identifiant'].isin(excl_fournisseur), 'Exclusion Reason'] = 'Exclus: Fournisseur'
    data.loc[data['Marque : identifiant'].isin(excl_marque), 'Exclusion Reason'] = 'Exclus: Marque'

    merged = data.merge(combi_df, how='left',
                        left_on=['Fournisseur : identifiant', 'Famille : identifiant'],
                        right_on=['Identifiant fournisseur', 'Identifiant famille'],
                        indicator=True)
    merged.loc[merged['_merge'] == 'both', 'Exclusion Reason'] = 'Exclus: Fournisseur-Famille'

    data_excluded = merged[merged['Exclusion Reason'].notna()].copy()
    data_processed = merged[merged['Exclusion Reason'].isna()].copy()
    return data_processed.drop(columns=['Identifiant fournisseur', 'Identifiant famille', '_merge']), \
           data_excluded.drop(columns=['Identifiant fournisseur', 'Identifiant famille', '_merge'])


def calculer_prix_promo(data: pd.DataFrame, remises: pd.DataFrame, price_column: str,
                        start_datetime: datetime, end_datetime: datetime):
    result, margin_issues, exclusion_from_calc = [], [], []

    for _, row in data.iterrows():
        prix_vente = row['Prix de vente en cours']
        prix_base = row[price_column]
        marge = round((prix_vente - prix_base) / prix_vente * 100, 2)
        remise_appliquee, remise_raison = 0, ""

        for _, r in remises.iterrows():
            if r['Marge minimale'] <= marge <= r['Marge maximale']:
                remise_appliquee = r['Remise'] / 100
                remise_raison = f"{r['Remise']}% (Marge {r['Marge minimale']}% - {r['Marge maximale']}%)"
                break

        prix_promo = round(prix_vente * (1 - remise_appliquee), 2)
        base_marge = row["Prix d'achat avec option"]
        taux_marge_promo = round((prix_promo - base_marge) / prix_promo * 100, 2)

        if prix_vente != prix_promo and pd.notna(taux_marge_promo):
            result.append({
                'Identifiant produit': row['Identifiant produit'],
                'Prix promo HT': str(prix_promo).replace('.', ','),
                'Date de début prix promo': start_datetime.strftime('%d/%m/%Y %H:%M:%S'),
                'Date de fin prix promo': end_datetime.strftime('%d/%m/%Y %H:%M:%S'),
                'Taux marge prix promo': str(taux_marge_promo).replace('.', ',')
            })
            if taux_marge_promo < 5 or taux_marge_promo > 80:
                margin_issues.append({
                    'Code produit': row['Code produit'],
                    'Prix de vente en cours': prix_vente,
                    "Prix d'achat avec option": row["Prix d'achat avec option"],
                    'Prix de revient': row['Prix de revient'],
                    'Prix promo calculé': prix_promo
                })
        else:
            exclusion_from_calc.append({
                'Code produit': row['Code produit'],
                'Raison exclusion': 'Prix promo supérieur ou égal au prix de vente',
                'Prix de vente en cours': prix_vente,
                "Prix d'achat avec option": row["Prix d'achat avec option"],
                'Prix de revient': row['Prix de revient'],
                'Remise appliquée': remise_appliquee * 100,
                'Raison de la remise': remise_raison
            })

    return pd.DataFrame(result), pd.DataFrame(margin_issues), pd.DataFrame(exclusion_from_calc)
