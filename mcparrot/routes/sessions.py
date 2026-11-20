import os

from flask import Blueprint, jsonify, request, send_from_directory

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

@sessions_bp.route("/get-plan", methods=["GET"])
def get_plan():
    session_name = request.args.get("session")
    plan_type = request.args.get("type")

    if not session_name or not plan_type:
        return jsonify({"error": "Missing session or type"}), 400

    # Remove .json extension if present to match folder naming
    clean_session_name = session_name.replace(".json", "")
    plan_dir = os.path.join("static", "plans", f"{clean_session_name}_plans")

    # Filenames
    filename_map = {
        "summary": "summary.md",
        "recon": "recon_plan.md",
        "va": "va_plan.md",
        "exploit": "exploit_plan.md"
    }

    filename = filename_map.get(plan_type)
    if not filename:
        return jsonify({"error": "Invalid plan type"}), 400

    filepath = os.path.join(plan_dir, filename)

    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"content": content})
        except Exception as e:
            return jsonify({"error": f"Failed to read file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Plan file not found. Make sure the plan has been generated for this session."}), 404
