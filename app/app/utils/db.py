import psycopg2
from flask import current_app


def get_db_connection():
    return psycopg2.connect(current_app.config["DATABASE_CONNECTION_STRING"])
