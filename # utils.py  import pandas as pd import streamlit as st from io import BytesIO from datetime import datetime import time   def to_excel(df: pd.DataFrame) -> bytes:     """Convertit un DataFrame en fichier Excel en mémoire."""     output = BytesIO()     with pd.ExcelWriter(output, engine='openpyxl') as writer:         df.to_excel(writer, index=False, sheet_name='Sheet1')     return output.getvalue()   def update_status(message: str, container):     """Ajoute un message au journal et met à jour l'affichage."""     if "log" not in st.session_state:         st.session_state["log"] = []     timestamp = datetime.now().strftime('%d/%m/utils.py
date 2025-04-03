# utils.py

import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
import time


def to_excel(df: pd.DataFrame) -> bytes:
    """Convertit un DataFrame en fichier Excel en mémoire."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()


def update_status(message: str, container):
    """Ajoute un message au journal et met à jour l'affichage."""
    if "log" not in st.session_state:
        st.session_state["log"] = []
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    st.session_state["log"].append(f"{timestamp} - {message}")
    log_display = "\n".join(st.session_state["log"])
    container.text_area("Journal des actions", log_display, height=200, disabled=True)
    time.sleep(0.1)


def load_file(label: str) -> BytesIO:
    """Charge un fichier Excel depuis l'utilisateur."""
    return st.file_uploader(f"Charger le fichier {label}", type=["xlsx"], key=label)
