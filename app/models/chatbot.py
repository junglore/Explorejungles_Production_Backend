"""
Chatbot conversation model for FaunaBot interactions
"""

from sqlalchemy import Column, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class ChatbotConversation(Base):
    __tablename__ = "chatbot_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Anonymous users allowed
    
    # Store conversation as JSON array
    # Format: [{"role": "user", "message": "...", "timestamp": "..."}, {"role": "bot", "message": "...", "timestamp": "..."}]
    messages = Column(JSON, default=list)
    
    # Conversation metadata
    conversation_metadata = Column(JSON, default=dict)  # Topics discussed, user satisfaction, etc.
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="chatbot_conversations")

    def __repr__(self):
        return f"<ChatbotConversation(id={self.id}, user_id={self.user_id}, messages_count={len(self.messages) if self.messages else 0})>"
