import os
from datetime import datetime
import psycopg2
from psycopg2 import sql
from google.cloud.sql.connector import Connector

connector = Connector()
CREDENTIALS_DIR = os.path.join('./', 'credentials')
postgres_password = os.path.join('PG_PASS')
postgres_username = os.path.join('PG_USER')


class ChatLogger:
    def __init__(self, db_name="babble", user="drunr_admin", password=postgres_password, host='localhost', port=5432, table_name='user_chats'):
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.table_name = table_name

        # self.conn = psycopg2.connect(
        #     dbname=self.db_name,
        #     user=self.user, 
        #     password="drunr_pass",
        #     host=self.host,
        #     port=self.port,
        # )

        self.conn = connector.connect(
            "drunr-prod:us-west1:drunr"
            "pg8000", # driver
            user=user,
            password=password,
            db=db_name
        )

        self.create_table()
        # self.conn.close()


    def create_table(self):
        with self.conn.cursor() as cur:
            cur.execute(sql.SQL(f"""
                DROP TABLE IF EXISTS {self.table_name};
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender VARCHAR(10) NOT NULL CHECK (sender IN ('user', 'bot')),
                    message TEXT NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """))
        self.conn.commit()


    def select_all_messages(self, session_id):
        data_list = []
        print("session_id: ", session_id)
        with self.conn.cursor() as cur:
            query = sql.SQL("SELECT * FROM {} WHERE session_id = {} ").format(sql.Identifier(self.table_name), sql.Literal(session_id))
            cur.execute(query)

            column_names = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            for row in rows:
                row_dict = {}
                for i, column_name in enumerate(column_names):
                    row_dict[column_name] = row[i]
                data_list.append(row_dict)
            return data_list


    def insert_message(self, session_id, sender, message):
        if sender not in ('user', 'bot'):
            raise ValueError("Sender must be 'user' or 'bot'")

        with self.conn.cursor() as cur:
            cur.execute(sql.SQL(f"""
                INSERT INTO {self.table_name} (session_id, sender, message, timestamp)
                VALUES (%s, %s, %s, %s);
            """), (str(session_id), sender, message, datetime.now()))
        self.conn.commit()


    def close(self):
        self.conn.close()

