import os

from flask import Blueprint, send_from_directory

sessions_bp = Blueprint('sessions', __name__)

@sessions_bp.route("/get-sessions")
def get_sessions():
    sessions = []
    sessions_dir = 'sessions'
    if os.path.exists(sessions_dir):
        for file in os.listdir(sessions_dir):
            if file.endswith('.json'):
                sessions.append(file)
    sessions.sort()
    return {"sessions": sessions}

@sessions_bp.route("/sessions/<filename>")
def serve_session(filename):
    sessions_dir = 'sessions'
    return send_from_directory(sessions_dir, filename)
