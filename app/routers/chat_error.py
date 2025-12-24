"""
Chat Routes for AI Book Assistant
Implements SSE (Server-Sent Events) for real-time chat
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
import requests

from app.models.database import get_db
from app.services.book_service import BookService, SessionService
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Store active chat sessions in memory (in production, use Redis)
active_chats = {}
# Track which clients have received which messages
client_sent_messages = {}

@router.post("/send")
async def send_message(
    message: str,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Send a message to the AI assistant
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
        
        # Process message with AI (async)
        asyncio.create_task(process_ai_response(session_id, message, db))
        
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
    SSE endpoint for streaming chat responses
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events"""
        client_id = str(uuid.uuid4())
        logger.info(f"Client {client_id} connected to session {session_id}")
        
        # Initialize client tracking
        if client_id not in client_sent_messages:
            client_sent_messages[client_id] = set()
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        # Track last sent index for this client
        last_sent_index = 0
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get messages for this session
                if session_id in active_chats:
                    messages = active_chats[session_id]
                    
                    # Only send NEW messages (not sent to this client yet)
                    for i in range(last_sent_index, len(messages)):
                        msg = messages[i]
                        msg_key = f"{msg['id']}_{msg.get('status', 'initial')}"
                        
                        # Check if we already sent this exact message+status combo
                        if msg_key not in client_sent_messages[client_id]:
                            # Send message
                            yield f"data: {json.dumps(msg)}\n\n"
                            client_sent_messages[client_id].add(msg_key)
                    
                    # Update last sent index
                    last_sent_index = len(messages)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info(f"Client {client_id} disconnected from session {session_id}")
            raise
        finally:
            logger.info(f"Cleaning up client {client_id}")
            # Clean up client tracking
            if client_id in client_sent_messages:
                del client_sent_messages[client_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

async def process_ai_response(session_id: str, user_message: str, db: Session):
    """
    Process user message through n8n webhook
    """
    try:
        response_id = str(uuid.uuid4())
        
        # Add "thinking" status message
        thinking_msg = {
            "id": response_id,
            "role": "assistant",
            "content": "...",
            "status": "thinking",
            "timestamp": datetime.now().isoformat()
        }
        active_chats[session_id].append(thinking_msg)
        
        # Call n8n webhook
        n8n_url = "http://n8n:5678/webhook/invoke_n8n_agent"
        
        try:
            # Prepare payload for n8n
            payload = {
                "sessionId": session_id,
                "chatInput": user_message
            }
            
            # Make request to n8n
            response = requests.post(
                n8n_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response_text = result.get("output", "I couldn't process your request.")
                
                # Parse response for book actions
                ai_response = await parse_ai_response(ai_response_text, db)
            else:
                logger.error(f"n8n webhook returned {response.status_code}: {response.text}")
                ai_response = {
                    "content": "I'm having trouble connecting to the AI service. Please try again later."
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to n8n: {e}")
            # Fallback to local response
            ai_response = await generate_ai_response(user_message, db)
        
        # IMPORTANT FIX: Replace the thinking message instead of updating
        # Remove the thinking message
        active_chats[session_id] = [
            msg for msg in active_chats[session_id] 
            if msg.get('id') != response_id
        ]
        
        # Add the complete message as NEW
        complete_msg = {
            "id": response_id,
            "role": "assistant",
            "content": ai_response['content'],
            "status": "complete",
            "timestamp": datetime.now().isoformat()
        }
        if 'actions' in ai_response:
            complete_msg['actions'] = ai_response['actions']
        
        active_chats[session_id].append(complete_msg)
        
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        error_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": f"Sorry, I encountered an error: {str(e)}",
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
        active_chats[session_id].append(error_msg)

async def parse_ai_response(response_text: str, db: Session) -> dict:
    """
    Parse AI response and extract book actions
    """
    response_lower = response_text.lower()
    
    # Check for book search results
    if "found" in response_lower and "book" in response_lower:
        # Extract book titles (simple pattern matching)
        # This would be enhanced based on n8n response format
        return {"content": response_text}
    
    # Check for save book commands
    if "save" in response_lower and any(word in response_lower for word in ["book", "added", "list"]):
        # Extract book ID if mentioned
        import re
        book_id_match = re.search(r'book\s*#?(\d+)', response_lower)
        if book_id_match:
            book_id = int(book_id_match.group(1))
            return {
                "content": response_text,
                "actions": {
                    "type": "save_book",
                    "book_id": book_id
                }
            }
    
    return {"content": response_text}

async def generate_ai_response(message: str, db: Session) -> dict:
    """
    Generate AI response based on message content
    This is a placeholder - will be replaced with actual AI integration
    """
    message_lower = message.lower()
    
    # Search for books
    if any(word in message_lower for word in ['search', 'find', 'looking for', 'book about']):
        # Extract search query (simple approach)
        search_terms = message.replace('search', '').replace('find', '').replace('looking for', '').replace('book about', '').strip()
        
        books = BookService.search_books(db, search_terms)[:3]
        
        if books:
            response = f"I found {len(books)} books matching your search:\n\n"
            book_data = []
            for book in books:
                response += f"📚 **{book.title}** by {book.author}\n"
                if book.rating:
                    response += f"   ⭐ Rating: {book.rating}/5\n"
                book_data.append({
                    "id": book.id,
                    "title": book.title,
                    "author": book.author
                })
            
            return {
                "content": response,
                "actions": {
                    "type": "book_results",
                    "books": book_data
                }
            }
        else:
            return {"content": "I couldn't find any books matching your search. Try different keywords!"}
    
    # Get recommendations
    elif any(word in message_lower for word in ['recommend', 'suggestion', 'what should i read']):
        books = BookService.get_featured_books(db, limit=3)
        
        response = "Here are some books I recommend:\n\n"
        for book in books:
            response += f"📖 **{book.title}** by {book.author}\n"
            if book.genres:
                response += f"   Genre: {', '.join([g.name for g in book.genres])}\n"
        
        return {"content": response}
    
    # Save book
    elif 'save' in message_lower and any(char.isdigit() for char in message):
        # Extract book ID (simple approach)
        book_id = ''.join(filter(str.isdigit, message))
        if book_id:
            return {
                "content": f"I'll save book #{book_id} to your list!",
                "actions": {
                    "type": "save_book",
                    "book_id": int(book_id)
                }
            }
    
    # Default response
    else:
        return {
            "content": "I'm your AI Book Assistant! I can help you:\n"
                      "• Search for books (e.g., 'search science fiction')\n"
                      "• Get recommendations (e.g., 'recommend me a book')\n"
                      "• Save books to your list (e.g., 'save book 1')\n\n"
                      "What would you like to do?"
        }

@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get chat history for a session
    """
    if session_id not in active_chats:
        return {"messages": []}
    
    messages = active_chats[session_id]
    return {
        "session_id": session_id,
        "messages": messages[-limit:],
        "total": len(messages)
    }

@router.delete("/clear/{session_id}")
async def clear_chat(session_id: str):
    """
    Clear chat history for a session
    """
    if session_id in active_chats:
        active_chats[session_id] = []
    
    return {"success": True, "message": "Chat history cleared"}
