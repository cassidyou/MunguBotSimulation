# main.py
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, ChatSession, Message

# create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

executor = ThreadPoolExecutor(max_workers=4)

# Simple connection manager: chat_id -> set of websockets
class ConnectionManager:
    def __init__(self):
        self.active: dict = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.active:
            self.active[chat_id] = set()
        self.active[chat_id].add(websocket)
        print(f"Client connected to chat {chat_id}. Total connections: {len(self.active[chat_id])}")

    def disconnect(self, chat_id: int, websocket: WebSocket):
        if chat_id in self.active and websocket in self.active[chat_id]:
            self.active[chat_id].remove(websocket)
            print(f"Client disconnected from chat {chat_id}. Total connections: {len(self.active.get(chat_id, set()))}")
            if not self.active[chat_id]:
                del self.active[chat_id]

    async def broadcast(self, chat_id: int, message: dict):
        if chat_id in self.active:
            disconnected = set()
            for ws in list(self.active[chat_id]):  # Create a copy to avoid modification during iteration
                try:
                    await ws.send_text(json.dumps(message))
                except Exception as e:
                    print(f"Error sending message to websocket: {e}")
                    disconnected.add(ws)
            
            # Remove disconnected clients
            for ws in disconnected:
                self.disconnect(chat_id, ws)
                
            if disconnected:
                print(f"Removed {len(disconnected)} disconnected clients from chat {chat_id}")

manager = ConnectionManager()

# ========== Utility DB helpers (run in threadpool) ==========
def get_unassigned_chat_and_assign(user_identifier=None):
    db: Session = SessionLocal()
    try:
        chat = None
        
        # If user_identifier is provided, try to find an existing chat for this user
        if user_identifier:
            chat = db.query(ChatSession).filter(
                ChatSession.user_identifier == user_identifier,
                ChatSession.is_active == True
            ).first()
        
        # If no existing chat found for user, look for unassigned chat
        if not chat:
            chat = db.query(ChatSession).filter(
                ChatSession.assigned_to == None, 
                ChatSession.is_active == True
            ).first()
        
        if chat:
            token = str(uuid.uuid4())
            chat.assigned_to = token
            # Set user_identifier if not already set
            if not chat.user_identifier and user_identifier:
                chat.user_identifier = user_identifier
            elif not chat.user_identifier:
                chat.user_identifier = str(uuid.uuid4())
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return {
                "chat_id": chat.id, 
                "token": token,
                "user_identifier": chat.user_identifier
            }
        
        # no unassigned chat -> create new
        chat = ChatSession()
        token = str(uuid.uuid4())
        chat.assigned_to = token
        chat.user_identifier = user_identifier if user_identifier else str(uuid.uuid4())
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return {
            "chat_id": chat.id, 
            "token": token,
            "user_identifier": chat.user_identifier
        }
    finally:
        db.close()

def set_user_identifier(chat_id: int, user_identifier: str):
    db = SessionLocal()
    try:
        chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        if chat:
            chat.user_identifier = user_identifier
            db.add(chat)
            db.commit()
            db.refresh(chat)
    finally:
        db.close()

def release_chat_db(chat_id: int):
    db = SessionLocal()
    try:
        c = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
        if not c:
            return {"ok": False, "error": "not found"}
        c.assigned_to = None
        db.add(c)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

def list_chats_db():
    db = SessionLocal()
    try:
        chats = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
        out = []
        for c in chats:
            out.append({
                "id": c.id,
                "assigned_to": c.assigned_to,
                "created_at": c.created_at.isoformat(),
            })
        return out
    finally:
        db.close()

def get_messages_db(chat_id: int):
    db = SessionLocal()
    try:
        msgs = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp).all()
        out = []
        for m in msgs:
            out.append({
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            })
        return out
    finally:
        db.close()

def save_message_db(chat_id: int, sender: str, content: str):
    db = SessionLocal()
    try:
        msg = Message(chat_id=chat_id, sender=sender, content=content)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return {
            "id": msg.id,
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        }
    finally:
        db.close()

def delete_all_messages():
    """
    Delete all records from the messages table.
    Returns the number of records deleted.
    """
    db = SessionLocal()
    try:
        # Count records before deletion
        count = db.query(Message).count()
        
        # Delete all messages
        db.query(Message).delete()
        db.commit()
        
        return True
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

def delete_all_chat_sessions():
    """
    Delete all records from the chat_sessions table.
    Returns the number of records deleted.
    """
    db = SessionLocal()
    try:
        # Count records before deletion
        count = db.query(ChatSession).count()
        
        # Delete all chat sessions
        db.query(ChatSession).delete()
        db.commit()
        
        return True
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


# ========== Routes ==========
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse("Use /chat/claimed for user or /admin/lists for admin")

@app.get('/login')
async def login():
    return HTMLResponse(open("static/login.html").read())

@app.get('/chat/lobby')
async def lobby():
    return HTMLResponse(open("static/lobby.html").read())

# user chat page
@app.get("/chat/claimed", response_class=HTMLResponse)
async def user_chat(request: Request):
    # Check if user has a user_identifier cookie
    user_identifier = request.cookies.get("user_identifier")
    
    # Pass the user_identifier to the template
    return templates.TemplateResponse("user_chat.html", {"request": request, "user_identifier": user_identifier})

# admin lists page
@app.get("/admin/lists", response_class=HTMLResponse)
async def admin_lists(request: Request):
    return templates.TemplateResponse("admin_list.html", {"request": request})

# admin single chat view
@app.get("/admin/lists/chat", response_class=HTMLResponse)
async def admin_chat_view(request: Request, chat_id: int):
    return templates.TemplateResponse("admin_chat.html", {"request": request, "chat_id": chat_id})

# assign chat for visiting user
@app.post("/api/chats/assign")
async def assign_chat(request: Request):
    # Get user_identifier from request body
    try:
        body = await request.json()
        user_identifier = body.get("user_identifier")
    except:
        user_identifier = None
    
    # Also check cookie as fallback
    if not user_identifier:
        user_identifier = request.cookies.get("user_identifier")
    
    result = await run_in_threadpool(lambda: get_unassigned_chat_and_assign(user_identifier))
    
    # Set user_identifier cookie if not already set
    response = JSONResponse(result)
    if not request.cookies.get("user_identifier") and result.get("user_identifier"):
        response.set_cookie(key="user_identifier", value=result["user_identifier"], max_age=30*24*60*60)  # 30 days
    
    return response

# release chat (logout)
@app.get("/api/chats/{chat_id}/release")
async def release_chat(chat_id: int):
    result = await run_in_threadpool(lambda: release_chat_db(chat_id))
    return JSONResponse(result)

# Delete all messages and chat sessions
@app.get('/api/chats/delete_all')
async def deleteAll():
    result = await run_in_threadpool(lambda: delete_all_messages())
    if result:
        result2 = await run_in_threadpool(lambda: delete_all_chat_sessions())
        return JSONResponse(result2)
    return JSONResponse(result)

# list chats (for admin)
@app.get("/api/chats")
async def api_list_chats():
    out = await run_in_threadpool(list_chats_db)
    return JSONResponse(out)

# get messages
@app.get("/api/messages/{chat_id}")
async def api_get_messages(chat_id: int):
    out = await run_in_threadpool(lambda: get_messages_db(chat_id))
    return JSONResponse(out)

# websocket endpoint (single endpoint for both roles)
@app.websocket("/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: int):
    # role and token are passed as query params: ?role=user&token=...
    params = dict(websocket.query_params)
    role = params.get("role", "user")
    token = params.get("token", "")

    # validate if user: ensure token matches assigned chat (if assigned)
    def _validate():
        db = SessionLocal()
        try:
            chat = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
            if not chat:
                return False, "chat not found"
            if role == "user":
                # If chat has assigned_to, token must match. If not assigned, it's allowed? For demo we assume assignment done server-side.
                if chat.assigned_to and token and chat.assigned_to != token:
                    return False, "token mismatch"
            return True, ""
        finally:
            db.close()

    ok, reason = await run_in_threadpool(_validate)
    if not ok:
        await websocket.close(code=4001)
        return

    await manager.connect(chat_id, websocket)
    try:
        # send history on connect
        recent = await run_in_threadpool(lambda: get_messages_db(chat_id))
        await websocket.send_text(json.dumps({"type": "history", "messages": recent}))

        while True:
            data = await websocket.receive_text()
            # Parse the message as JSON
            try:
                payload = json.loads(data)
                sender = payload.get("sender", role)
                content = payload.get("content", "")
            except json.JSONDecodeError:
                # If not JSON, treat as plain text from user
                sender = role
                content = data
            
            if not content:
                continue
                
            # Save message to database
            saved = await run_in_threadpool(lambda: save_message_db(chat_id, sender, content))
            # Broadcast to all connected clients for this chat
            await manager.broadcast(chat_id, {"type": "message", "message": saved})
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(chat_id, websocket)
