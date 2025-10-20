# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    assigned_to = Column(String, nullable=True, index=True)  # token or None
    user_identifier = Column(String, nullable=True, index=True)  # for identifying returning users
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chat_sessions.id"))
    sender = Column(String)  # "admin" or "user"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    chat = relationship("ChatSession", back_populates="messages")