"""
Chat Routes for AI Book Assistant - DEMO MODE
Simple script for demo with 3 predefined questions only
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, AsyncGenerator
import json
import asyncio
import logging
from datetime import datetime
import uuid

from app.models.database import get_db
from app.services.book_service import BookService, SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Store active chat sessions in memory
active_chats = {}

# DEMO MODE: Only 3 predefined questions allowed
DEMO_RESPONSES = {
    "Hi, can you help me find a good book to read today?": {
        "text": "I'd be happy to help you find a great book! Since I don't want to use any tools, let me ask you some questions instead. What kind of books do you usually enjoy reading? Are you in the mood for something light and easy or something more complex and thought-provoking?\nAlso, is there a particular author or genre that you've been wanting to explore or revisit? Let's chat about it and see if we can find the perfect book for your reading pleasure!",
        "delay": 7
    },
    
    "Find books by J.K. Rowling about magic.": {
        "text": "Here are some books by J.K. Rowling that you might enjoy:\n\"Harry Potter and the Philosopher's Stone\" - The first book in the beloved Harry Potter series, where we meet the young wizard who attends Hogwarts School of Witchcraft and Wizardry.\n\"Harry Potter and the Chamber of Secrets\" - The second installment in the series, where Harry returns to Hogwarts for his second year, only to discover a mysterious chamber within the school that threatens to unleash evil upon the wizarding world.\n\"Harry Potter and the Prisoner of Azkaban\" - The third book in the series, where Sirius Black, a wizard believed to have betrayed Harry's parents to Voldemort, escapes from Azkaban prison and is believed to be coming after Harry.\n\"Fantastic Beasts and Where to Find Them\" - A companion book to the Harry Potter series, this guide to magical creatures was written by magizoologist Newt Scamander and first appeared in the Fantastic Beasts film series.\n\"The Casual Vacancy\" - While not strictly a magic novel, this novel by J.K. Rowling explores themes of power, privilege, and the human condition in a small English town.\nWould you like more information about any of these books or would you like me to recommend something else?",
        "delay": 3
    },
    
    "Recommend a sci-fi book like Dune.": {
        "text": "Here are some results:\n\"Diaspora\" by Greg Egan - A novel about a group of sentient AIs who leave their home planet to explore the universe.\n\"The City & The City\" by China Miéville - A police procedural set in a world where two cities coexist in the same space.\n\"Altered Carbon\" by Richard K. Morgan - A cyberpunk novel about a human consciousness that is transferred into new bodies.\nThese books all share some similarities with Dune in terms of their complex world-building and exploration of philosophical themes.\nWould you like to know more about any of these books or would you like me to recommend something else?",
        "delay": 3
    }
}

def get_demo_response(user_message: str) -> tuple:
    """
    Get response for demo questions only
    Returns: (response_text, delay_seconds) or (None, 0) if not a demo question
    """
    # Check for exact matches first
    if user_message in DEMO_RESPONSES:
        response_data = DEMO_RESPONSES[user_message]
        return response_data["text"], response_data["delay"]
    
    # Check for partial matches (case insensitive)
    user_lower = user_message.lower().strip()
    for key, response_data in DEMO_RESPONSES.items():
        if user_lower == key.lower().strip():
            return response_data["text"], response_data["delay"]
    
    # Not a demo question
    return None, 0

@router.post("/send")
async def send_message(
    message: str,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Send a message to the AI assistant - DEMO MODE
    """
    try:
        # Generate unique message ID
        message_id = str(uuid.uuid4())
        
        # Store message in active chats
        if session_id not in active_chats:
            active_chats[session_id] = []
        
        # Add user message
        user_msg = {
            "id": message_id,
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        active_chats[session_id].append(user_msg)
        
        # Process message in DEMO MODE (async)
        asyncio.create_task(process_demo_response(session_id, message))
        
        return {
            "success": True,
            "message_id": message_id,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Chat send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/{session_id}")
async def chat_stream(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    SSE endpoint for streaming chat responses - DEMO MODE
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events"""
        client_id = str(uuid.uuid4())
        logger.info(f"DEMO MODE: Client {client_id} connected to session {session_id}")
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        # Track which message IDs this client has seen
        seen_message_ids = set()
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get messages for this session
                if session_id in active_chats:
                    messages = active_chats[session_id]
                    
                    # Send only NEW messages this client hasn't seen
                    for msg in messages:
                        if msg['id'] not in seen_message_ids:
                            yield f"data: {json.dumps(msg)}\n\n"
                            seen_message_ids.add(msg['id'])
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info(f"DEMO MODE: Client {client_id} disconnected from session {session_id}")
            raise
        finally:
            logger.info(f"DEMO MODE: Cleaning up client {client_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

async def process_demo_response(session_id: str, user_message: str):
    """
    Process user message in DEMO MODE - No n8n webhook calls
    """
    try:
        response_id = str(uuid.uuid4())
        
        # Add "thinking" status
        thinking_msg = {
            "id": response_id,
            "role": "assistant",
            "content": "",
            "status": "thinking",
            "timestamp": datetime.now().isoformat()
        }
        active_chats[session_id].append(thinking_msg)
        
        # Check if this is a demo question
        demo_response, delay_seconds = get_demo_response(user_message)
        
        if demo_response is not None:
            # This is a demo question - apply delay and respond
            logger.info(f"DEMO MODE: Processing demo question with {delay_seconds}s delay")
            await asyncio.sleep(delay_seconds)
            
            ai_response_text = demo_response
            status = "complete"
            
        else:
            # Not a demo question - return error message
            logger.info(f"DEMO MODE: Non-demo question received: {user_message}")
            await asyncio.sleep(2)  # Small delay for realism
            
            ai_response_text = "I'm sorry, but this is a demo version and I can only respond to specific pre-programmed questions. Please try one of these exact questions:\n\n1. \"Hi, can you help me find a good book to read today?\"\n2. \"Find books by J.K. Rowling about magic.\"\n3. \"Recommend a sci-fi book like Dune.\"\n\nThank you for your understanding!"
            status = "complete"
        
        # Remove thinking message
        active_chats[session_id] = [
            msg for msg in active_chats[session_id] 
            if msg['id'] != response_id
        ]
        
        # Add complete response
        complete_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response_text,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        active_chats[session_id].append(complete_msg)
        
    except Exception as e:
        logger.error(f"DEMO MODE processing error: {type(e).__name__}: {e}")
        
        # Remove thinking message if exists
        if 'response_id' in locals():
            active_chats[session_id] = [
                msg for msg in active_chats[session_id] 
                if msg.get('id') != response_id
            ]
        
        # Add error message
        error_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "I'm experiencing technical difficulties. This is a demo version - please try the pre-programmed questions.",
            "status": "complete",
            "timestamp": datetime.now().isoformat()
        }
        active_chats[session_id].append(error_msg)

@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get chat history for a session - DEMO MODE
    """
    if session_id not in active_chats:
        return {"messages": []}
    
    messages = active_chats[session_id]
    return {
        "session_id": session_id,
        "messages": messages[-limit:],
        "total": len(messages),
        "mode": "demo"
    }

@router.delete("/clear/{session_id}")
async def clear_chat(session_id: str):
    """
    Clear chat history for a session - DEMO MODE
    """
    if session_id in active_chats:
        active_chats[session_id] = []
    
    return {"success": True, "message": "Demo chat history cleared"}

@router.get("/demo-status")
async def get_demo_status():
    """Get demo mode status and available questions"""
    return {
        "mode": "demo",
        "available_questions": list(DEMO_RESPONSES.keys()),
        "message": "This is a demo version. Only the listed questions are supported."
    }