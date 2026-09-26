import os
import threading
import json
import base64
import asyncio
import cv2
import websockets
from flask import Flask, render_template, send_from_directory
import config

# Create Flask App
# Specify correct template folder (absolute path to workspace templates folder)
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)

@app.route('/')
def index():
    return render_template('smartboard.html')

@app.route('/profile/<student_id>')
def get_profile(student_id):
    student_dir = os.path.join(config.DATASET_DIR, student_id)
    profile_path = os.path.join(student_dir, "profile.jpg")
    if os.path.exists(profile_path):
        return send_from_directory(student_dir, "profile.jpg")
    else:
        # Check if there is another image in the folder
        if os.path.exists(student_dir):
            images = [img for img in os.listdir(student_dir) if img.endswith(".jpg") and img != "profile.jpg"]
            if images:
                return send_from_directory(student_dir, sorted(images)[0])
        # Return fallback status/error
        return "No profile picture", 404

# WebSocket connection logic
connected_sockets = set()
ws_loop = None
is_active = False
last_attendance = None

async def ws_handler(websocket):
    global is_active, last_attendance
    connected_sockets.add(websocket)
    try:
        # Send current state
        await websocket.send(json.dumps({
            "type": "status",
            "active": is_active
        }))
        if last_attendance:
            await websocket.send(json.dumps({
                "type": "attendance",
                **last_attendance
            }))
        
        # Keep client connection open
        async for message in websocket:
            pass
    except Exception:
        pass
    finally:
        if websocket in connected_sockets:
            connected_sockets.remove(websocket)

async def ws_main():
    # Bind to all interfaces so smartboards on network can connect
    async with websockets.serve(ws_handler, "0.0.0.0", 5001):
        await asyncio.Future()

def run_ws_loop():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    ws_loop.run_until_complete(ws_main())

def run_flask():
    # Flask runs in threaded mode
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

def start_servers():
    """Starts the Flask and WebSocket servers in background threads."""
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    ws_thread = threading.Thread(target=run_ws_loop, daemon=True)
    flask_thread.start()
    ws_thread.start()
    print("Smartboard HTTP server started on http://localhost:5000")
    print("Smartboard WebSocket server started on ws://localhost:5001")

def broadcast_to_sockets(message_dict):
    global ws_loop, connected_sockets
    if not connected_sockets or ws_loop is None:
        return
        
    async def do_send():
        payload = json.dumps(message_dict)
        for ws in list(connected_sockets):
            try:
                await ws.send(payload)
            except Exception:
                pass
                
    ws_loop.call_soon_threadsafe(lambda: asyncio.run_coroutine_threadsafe(do_send(), ws_loop))

def notify_session_status(active):
    global is_active, last_attendance
    is_active = active
    if not active:
        last_attendance = None
    broadcast_to_sockets({
        "type": "status",
        "active": active
    })

def notify_attendance(student_id, name, class_name, section, time_str, confidence_pct):
    global last_attendance
    last_attendance = {
        "student_id": student_id,
        "name": name,
        "class_name": class_name,
        "section": section,
        "time": time_str,
        "confidence": confidence_pct,
        "profile_url": f"/profile/{student_id}"
    }
    
    broadcast_to_sockets({
        "type": "attendance",
        **last_attendance
    })

def notify_frame(frame, fps=None):
    try:
        h, w = frame.shape[:2]
        # Resize to 640 width if frame is larger, keeping aspect ratio, to optimize network
        if w > 640:
            scale = 640 / w
            frame = cv2.resize(frame, (640, int(h * scale)), interpolation=cv2.INTER_AREA)
            
        _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        b64_data = base64.b64encode(jpeg).decode('utf-8')
        
        msg = {
            "type": "frame",
            "image": "data:image/jpeg;base64," + b64_data
        }
        if fps is not None:
            msg["fps"] = f"{fps:.1f}"
            
        broadcast_to_sockets(msg)
    except Exception as e:
        print(f"Error encoding/broadcasting frame: {e}")
