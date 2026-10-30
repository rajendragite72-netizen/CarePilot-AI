from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Conversation, Message, ExtractedFact, User
from app.services.ai_provider import get_ai_provider


def get_patient_context(db: Session, patient_id: int) -> List[Dict[str, Any]]:
    """Get all confirmed facts for a patient to use as AI context."""
    facts = db.query(ExtractedFact).filter(
        ExtractedFact.patient_id == patient_id,
        ExtractedFact.status.in_(["patient_confirmed", "clinician_reviewed"])
    ).all()
    
    return [
        {
            "fact_type": fact.fact_type,
            "extracted_value": fact.extracted_value,
            "source_text": fact.source_text,
            "page_number": fact.page_number,
            "document_id": fact.document_id,
            "uncertainty_reason": fact.uncertainty_reason,
        }
        for fact in facts
    ]


def create_conversation(db: Session, patient_id: int, title: Optional[str] = None) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
        patient_id=patient_id,
        title=title or "New Conversation",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: int, patient_id: int) -> Optional[Conversation]:
    """Get conversation by ID, ensuring it belongs to the patient."""
    return db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.patient_id == patient_id
    ).first()


def get_patient_conversations(db: Session, patient_id: int) -> List[Conversation]:
    """Get all conversations for a patient."""
    return db.query(Conversation).filter(
        Conversation.patient_id == patient_id
    ).order_by(Conversation.updated_at.desc()).all()


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None
) -> Message:
    """Add a message to a conversation."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
    )
    db.add(message)
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    return message


def get_conversation_messages(db: Session, conversation_id: int) -> List[Message]:
    """Get all messages in a conversation."""
    return db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()


async def chat_with_ai(
    db: Session,
    patient_id: int,
    message: str,
    conversation_id: Optional[int] = None
) -> tuple[str, List[Dict[str, Any]], int]:
    """Process a chat message and return AI response with sources."""
    if conversation_id:
        conversation = get_conversation(db, conversation_id, patient_id)
        if not conversation:
            raise ValueError("Conversation not found")
    else:
        conversation = create_conversation(db, patient_id)
    
    add_message(db, conversation.id, "user", message)
    
    context = get_patient_context(db, patient_id)
    
    messages = get_conversation_messages(db, conversation.id)
    ai_messages = [{"role": m.role, "content": m.content} for m in messages]
    
    provider = get_ai_provider()
    response = await provider.generate_response(ai_messages, context)
    
    sources = [
        {
            "fact_type": c["fact_type"],
            "value": c["extracted_value"],
            "page": c["page_number"],
            "document_id": c["document_id"],
        }
        for c in context
    ]
    
    add_message(db, conversation.id, "assistant", response, sources)
    
    return response, sources, conversation.id