import os

import psycopg
import streamlit as st
from psycopg.rows import dict_row
from streamlit.errors import StreamlitSecretNotFoundError


def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        try:
            database_url = st.secrets["DATABASE_URL"]
        except (KeyError, StreamlitSecretNotFoundError):
            database_url = None

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Add the Supabase connection URI "
            "to Streamlit Cloud Secrets."
        )
    return database_url


def get_db_connection():
    return psycopg.connect(
        get_database_url(),
        connect_timeout=10,
        prepare_threshold=None,
        row_factory=dict_row,
        sslmode="require",
    )
