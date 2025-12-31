"""
Chatbot API Routes
Handles chatbot conversations and AI interactions
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.db.database import get_db
from app.models.chatbot import ChatbotConversation
from app.models.user import User
from app.core.security import get_current_user, get_current_user_optional

router = APIRouter()

@router.get("/")
async def get_conversations(
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of conversations to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get user's chatbot conversations"""
    try:
        if current_user:
            # Get user's conversations
            result = await db.execute(
                select(ChatbotConversation)
                .where(ChatbotConversation.user_id == current_user.id)
                .order_by(desc(ChatbotConversation.started_at))
                .offset(skip)
                .limit(limit)
            )
        else:
            # For anonymous users, return empty list
            return []
        
        conversations = result.scalars().all()
        
        return [
            {
                "id": str(conv.id),
                "title": f"Conversation {conv.started_at.strftime('%Y-%m-%d %H:%M')}",
                "message_count": len(conv.messages) if conv.messages else 0,
                "started_at": conv.started_at.isoformat(),
                "last_message_at": conv.last_message_at.isoformat()
            }
            for conv in conversations
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversations: {str(e)}"
        )

@router.post("/")
async def create_conversation(
    message_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Create a new chatbot conversation or send a message"""
    try:
        user_message = message_data.get("message", "").strip()
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Simple chatbot response logic (placeholder)
        bot_response = generate_wildlife_response(user_message)
        
        # Create conversation record
        messages = [
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "role": "assistant",
                "content": bot_response,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        conversation = ChatbotConversation(
            user_id=current_user.id if current_user else None,
            messages=messages
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        return {
            "id": str(conversation.id),
            "user_message": user_message,
            "bot_response": bot_response,
            "created_at": conversation.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get specific conversation by ID"""
    try:
        query = select(ChatbotConversation).where(ChatbotConversation.id == conversation_id)
        
        # If user is logged in, ensure they own the conversation
        if current_user:
            query = query.where(ChatbotConversation.user_id == current_user.id)
        
        result = await db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return {
            "id": str(conversation.id),
            "messages": conversation.messages or [],
            "started_at": conversation.started_at.isoformat(),
            "last_message_at": conversation.last_message_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation: {str(e)}"
        )

@router.post("/{conversation_id}/message")
async def add_message_to_conversation(
    conversation_id: UUID,
    message_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Add a message to existing conversation"""
    try:
        user_message = message_data.get("message", "").strip()
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Get conversation
        query = select(ChatbotConversation).where(ChatbotConversation.id == conversation_id)
        if current_user:
            query = query.where(ChatbotConversation.user_id == current_user.id)
        
        result = await db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Generate bot response
        bot_response = generate_wildlife_response(user_message)
        
        # Add messages to conversation
        messages = conversation.messages or []
        messages.extend([
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "role": "assistant",
                "content": bot_response,
                "timestamp": datetime.utcnow().isoformat()
            }
        ])
        
        conversation.messages = messages
        await db.commit()
        
        return {
            "user_message": user_message,
            "bot_response": bot_response,
            "last_message_at": conversation.last_message_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )

def generate_wildlife_response(user_message: str) -> str:
    """Generate a simple wildlife-themed chatbot response"""
    message_lower = user_message.lower()
    
    # Simple keyword-based responses
    if any(word in message_lower for word in ["tiger", "tigers"]):
        return "Tigers are magnificent apex predators! Did you know that tigers are excellent swimmers and can leap horizontally up to 33 feet? There are currently 6 subspecies of tigers remaining in the wild. Would you like to learn more about tiger conservation efforts?"
    
    elif any(word in message_lower for word in ["elephant", "elephants"]):
        return "Elephants are incredible creatures with complex social structures! They have excellent memories and can recognize hundreds of individuals. African elephants are the largest land mammals on Earth. Are you interested in learning about elephant conservation programs?"
    
    elif any(word in message_lower for word in ["lion", "lions"]):
        return "Lions are known as the 'King of the Jungle' though they actually live in grasslands and savannas! They're the only cats that live in social groups called prides. A lion's roar can be heard up to 5 miles away. What would you like to know about lions?"
    
    elif any(word in message_lower for word in ["conservation", "protect", "save"]):
        return "Wildlife conservation is crucial for maintaining biodiversity and ecosystem balance. There are many ways to help: supporting conservation organizations, reducing plastic use, choosing sustainable products, and spreading awareness. Which conservation topic interests you most?"
    
    elif any(word in message_lower for word in ["forest", "jungle", "rainforest"]):
        return "Forests are the lungs of our planet! Tropical rainforests contain over half of the world's plant and animal species despite covering only 6% of Earth's surface. They play a vital role in climate regulation and carbon storage. Would you like to learn about forest conservation?"
    
    elif any(word in message_lower for word in ["bird", "birds"]):
        return "Birds are fascinating creatures! There are over 10,000 bird species worldwide. They play crucial roles as pollinators, seed dispersers, and pest controllers. Many bird species are excellent indicators of ecosystem health. Are you interested in birdwatching or bird conservation?"
    
    elif any(word in message_lower for word in ["ocean", "marine", "sea"]):
        return "Our oceans are home to incredible biodiversity! Marine ecosystems support countless species and provide essential services like climate regulation and oxygen production. Ocean conservation is critical as marine life faces threats from pollution, overfishing, and climate change. What marine topic interests you?"
    
    elif any(word in message_lower for word in ["hello", "hi", "hey"]):
        return "Hello! Welcome to Junglore's wildlife chatbot! 🌿 I'm here to help you learn about wildlife, conservation, and our amazing natural world. You can ask me about different animals, conservation efforts, or any wildlife-related topics. What would you like to explore today?"
    
    elif any(word in message_lower for word in ["help", "what can you do"]):
        return "I can help you with information about: 🦁 Wildlife and animals, 🌱 Conservation efforts, 🌍 Ecosystems and habitats, 📚 Educational content about nature, 🔍 Finding specific wildlife information. Just ask me about any animal or conservation topic you're curious about!"
    
    else:
        return "That's an interesting question about wildlife! While I'd love to provide more specific information, I'm still learning. For detailed information about wildlife and conservation, I recommend exploring our educational content or contacting our wildlife experts. Is there a specific animal or conservation topic you'd like to know more about?"