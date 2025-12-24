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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Store active chat sessions in memory
active_chats = {}

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
            logger.info(f"Client {client_id} disconnected from session {session_id}")
            raise
        finally:
            logger.info(f"Cleaning up client {client_id}")
    
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
        
        # Add "thinking" status
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
            
            logger.info(f"Calling n8n webhook with: {json.dumps(payload)}")
            
            # Make request to n8n
            response = requests.post(
                n8n_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            logger.info(f"N8N response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"N8N response structure: {json.dumps(result)[:200]}")
                
                # Handle nested output structure {"output": {"output": "..."}}
                if isinstance(result, dict):
                    # Check for nested output
                    if "output" in result and isinstance(result["output"], dict):
                        ai_response_text = result["output"].get("output", "")
                    # Check for direct output
                    elif "output" in result:
                        ai_response_text = result["output"]
                    # Try other common fields
                    else:
                        ai_response_text = (
                            result.get("response") or 
                            result.get("message") or 
                            result.get("text") or
                            str(result)
                        )
                else:
                    ai_response_text = str(result)
                
                if not ai_response_text:
                    ai_response_text = "I received an empty response. Please try again."
                
            else:
                logger.error(f"N8N webhook returned {response.status_code}: {response.text}")
                ai_response_text = f"Error: The AI service returned status {response.status_code}. Please try again."
                
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to n8n service")
            ai_response_text = "Cannot connect to the AI service. Please ensure n8n is running."
        except requests.exceptions.Timeout:
            logger.error("N8N request timeout")
            ai_response_text = "The AI service is taking too long to respond. Please try again."
        except Exception as e:
            logger.error(f"Error calling n8n: {type(e).__name__}: {e}")
            ai_response_text = f"An error occurred: {str(e)}"
        
        # Remove thinking message
        active_chats[session_id] = [
            msg for msg in active_chats[session_id] 
            if msg['id'] != response_id
        ]
        
        # Add complete message with new ID
        complete_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response_text,
            "status": "complete",
            "timestamp": datetime.now().isoformat()
        }
        
        active_chats[session_id].append(complete_msg)
        
    except Exception as e:
        logger.error(f"AI processing error: {type(e).__name__}: {e}")
        # Remove thinking message if exists
        active_chats[session_id] = [
            msg for msg in active_chats[session_id] 
            if msg.get('id') != response_id
        ]
        
        error_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": f"Sorry, I encountered an error: {str(e)}",
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
        active_chats[session_id].append(error_msg)

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

@router.get("/test-n8n")
async def test_n8n_connection():
    """Test n8n webhook connectivity"""
    try:
        response = requests.post(
            "http://n8n:5678/webhook/invoke_n8n_agent",
            json={"sessionId": "test", "chatInput": "hello"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        return {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "parsed": response.json() if response.status_code == 200 else None,
            "success": response.status_code == 200
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
