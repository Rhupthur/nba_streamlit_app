import pandas as pd
import streamlit as st
from io import BytesIO

# --- Fonction utilitaire pour export Excel (NOUVEAU) ---
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    return output.getvalue()

# chargement des données

@st.cache_data
def load_data():
    df_r = pd.read_csv('data_clean_regulier.csv')
    df_p = pd.read_csv('data_clean_playoffs.csv')
    return df_r, df_p

df_r, df_p = load_data()

# harmonisation des noms d'équipes entre les deux datasets
if "Team" in df_r.columns:
    df_r = df_r.rename(columns={"Team": "Team"})
if "Team" in df_p.columns:
    df_p = df_p.rename(columns={"Team": "Team"})

# ajouter une colonne pour indiquer la source des données
df_r['Source'] = "Saison régulière"
df_p['Source'] = "Playoffs"

# cofiguration de l'application
st.set_page_config(page_title="App de notoyage des donnees NBA", layout="wide")


# Interface utilisateur
st.title("🏀 Application NBA – Données Nettoyées")
st.write("Visualisation simple des datasets nettoyés (Saison régulière & Playoffs).")
st.caption("This is Dakar Institute of Technology")

# Sélection du dataset à afficher
st.sidebar.header("Filtres")
choix_saison = st.sidebar.radio("Choisissez la competition:", ("Régulière", "Playoffs"))

if choix_saison == "Régulière":
    df = df_r.copy()
elif choix_saison == "Playoffs":
    df = df_p.copy()
else:
    df = pd.concat([df_r, df_p], ignore_index=True)


# filtrage par équipe
if "Team" in df.columns:
    equipes = sorted(df["Team"].dropna().unique())
    equipes_selectionnees = st.sidebar.multiselect("Filtrer par équipe :", equipes, default=equipes)
    df = df[df["Team"].isin(equipes_selectionnees)]
else:
    st.warning("La colonne 'Team' est absente du dataset chargé.")
    

# filtrer minimun de matches joués
if "G" in df.columns:
    min_G = int(df["G"].min())
    max_G = int(df["G"].max())
    g_filtre = st.sidebar.slider("Nombre minimum de matches joués (G):", min_G, max_G, min_G)
    df = df[df["G"] >= g_filtre]


# onglet 1: vue generale
# onglet 2: top scoreurs
# onglet 3: comparaison joeur

tab1, tab2, tab3 = st.tabs(["Vue Générale", "Top Scoreurs", "Comparaison Joueurs"])

with tab1:
    st.subheader("Vue générale des données filtrées")

    col1, col2, col3, col4 = st.columns(4)

    nb_lignes = len(df)
    nb_joueurs = df["Player"].nunique() if "Player" in df.columns else nb_lignes
    moy_pts = df["PTS"].mean() if "PTS" in df.columns else None
    moy_ast = df["AST"].mean() if "AST" in df.columns else None

    col1.metric("Nombre de lignes", nb_lignes)
    col2.metric("Nombre de joueurs uniques", nb_joueurs)
    if moy_pts is not None:
        col3.metric("Moyenne de PTS", f"{moy_pts:.2f}")
    if moy_ast is not None:
        col4.metric("Moyenne de AST", f"{moy_ast:.2f}")

    st.write("Tableau complet")
    st.dataframe(df, use_container_width=True)

    # Export CSV des données filtrées
    st.download_button(
        label="📥 Télécharger les données filtrées (CSV)",
        data=df.to_csv(index=False),
        file_name="donnees_filtrees.csv",
        mime="text/csv"
    )

    # Export Excel des données filtrées
    excel_data = to_excel(df)
    st.download_button(
        label="📥 Télécharger les données filtrées (Excel)",
        data=excel_data,
        file_name="donnees_filtrees.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


with tab2:
    st.subheader("Top Scoreurs")

    if "PTS" in df.columns and "Player" in df.columns:
        try:
            df_pts = df.groupby("Player", as_index=False)["PTS"].mean()
            df_pts = df_pts.sort_values(by="PTS", ascending=False)

            top_n = st.slider("Sélectionnez le nombre de top scoreurs à afficher:", 5, 20, 10)
            df_top = df_pts.head(top_n).set_index("Player")

            st.bar_chart(df_top["PTS"])
            st.write("Tableau des top scoreurs :")
            st.dataframe(df_top)

            # Export CSV top scoreurs
            st.download_button(
                label="📥 Télécharger le Top Scoreurs (CSV)",
                data=df_top.to_csv(),
                file_name="top_scoreurs.csv",
                mime="text/csv"
            )

            # Export Excel top scoreurs
            excel_top = to_excel(df_top.reset_index())
            st.download_button(
                label="📥 Télécharger le Top Scoreurs (Excel)",
                data=excel_top,
                file_name="top_scoreurs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


        except Exception as e:
            st.error(f"Une erreur est survenue lors du calcul des top scoreurs: {e}")
    else:
        st.info("La colonne 'PTS' n'est pas disponible dans le dataset sélectionné.")


with tab3:
    st.subheader("🆚 Comparaison Saison régulière vs Playoffs")

    # on compare les joueurs presents dans les deux datasets
    if "Player" not in df_r.columns or "Player" not in df_p.columns:
        st.info("La colonne 'Player' est absente dans l'un des datasets.")
    else:
        joueurs_regulier = set(df_r["Player"].dropna().unique())
        joueurs_playoffs = set(df_p["Player"].dropna().unique())

    joueurs_communs = sorted(joueurs_regulier.intersection(joueurs_playoffs))

    if len(joueurs_communs) == 0:
        st.info("Aucun joueur commun trouvé entre la saison régulière et les playoffs.")
    else:
        joueur_choisi = st.selectbox("Choisir un joueur :", joueurs_communs)

        joueur_regulier = df_r[df_r["Player"] == joueur_choisi]
        joueur_playoffs = df_p[df_p["Player"] == joueur_choisi]

        agg_cols = ["PTS", "AST", "TRB", "STL", "BLK", "G", "MP"]
        cols_reg = [c for c in agg_cols if c in joueur_regulier.columns]
        cols_play = [c for c in agg_cols if c in joueur_playoffs.columns]

        stats_regulier = joueur_regulier[cols_reg].mean(numeric_only=True)
        stats_playoffs = joueur_playoffs[cols_play].mean(numeric_only=True)

        # Construction du tableau final, même si des colonnes manquent
        
        stats_comparaison = pd.DataFrame({
            "Stat": agg_cols,
            "Saison Régulière": [stats_regulier.get(c, None) for c in agg_cols],
            "Playoffs": [stats_playoffs.get(c, None) for c in agg_cols],
        })


        st.write(f"Comparaison des statistiques moyennes pour {joueur_choisi}")
        st.dataframe(stats_comparaison.set_index('Stat'))


        # Export CSV comparaison joueur
        st.download_button(
            label=f"📥 Télécharger la comparaison de {joueur_choisi} (CSV)",
            data=stats_comparaison.to_csv(index=False),
            file_name=f"comparaison_{joueur_choisi}.csv",
            mime="text/csv"
        )

        # Export Excel comparaison joueur
        excel_comp = to_excel(stats_comparaison)
        st.download_button(
            label=f"📥 Télécharger la comparaison de {joueur_choisi} (Excel)",
            data=excel_comp,
            file_name=f"comparaison_{joueur_choisi}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # graphique sur les points
        if not pd.isna(stats_regulier.get("PTS")) and not pd.isna(stats_playoffs.get("PTS")):
            pts_comp = pd.DataFrame({
                'Contexte': ['Saison Régulière', 'Playoffs'],
                'PTS': [stats_regulier["PTS"], stats_playoffs["PTS"]]
            }).set_index('Contexte')
            st.bar_chart(pts_comp)