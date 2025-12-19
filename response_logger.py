import os
import uuid
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:password@localhost:5432/mydatabase"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the ChatHistory model
class ChatHistory(Base):
    __tablename__ = "user_chats"
    session_id = Column(String, primary_key=True, index=True)
    sender = Column(String)
    message = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ChatLogger class for inserting and selecting chat history
class ChatLogger:

    @staticmethod
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def __init__(self, table_name='user_chats'):
        self.table_name = table_name

        # Create table(s)
        Base.metadata.create_all(bind=engine)

    def select_all_messages(self, session_id):
        print("session_id:", session_id)
        db = SessionLocal()
        try:
            records = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).all()
            print("records:", records)
            return records
        finally:
            db.close()

    def insert_message(self, session_id, sender, message):
        db = SessionLocal()
        try:
            record = ChatHistory(
                session_id=session_id,
                sender=sender,
                message=message,
                timestamp=datetime.utcnow()
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            print(f"✅ Stored chat data for {session_id} - {sender}")
        finally:
            db.close()
