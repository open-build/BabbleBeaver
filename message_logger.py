import sqlite3

"""
Log messages sent through the chatbot and allow for retrievening them later.
This is implemented in SQLListe for testing purposes.  Would be better to implement in 
a MongoDB or similar document-based database for scalability.

TODO: Create simple analytics for the chatbot, such as the number of messages sent, the most common messages, etc.
"""


class MessageLogger:
    def __init__(self, db_path="chatbot.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    type TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)

    def log_message(self, message, type):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (message, type) VALUES (?, ?)", (message, type))
            conn.commit()

    def retrieve_messages(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, type, message FROM messages")
            return cursor.fetchall()
