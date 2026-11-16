import os

from flask import Blueprint, request

from mcparrot.utils import config

settings_bp = Blueprint('settings', __name__)

# Updating config
@settings_bp.route("/update-config", methods=['POST'])
def update_config():
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')

        config.set_setting(key, value)

        return {"success": True, "message": f"Updated {key} to {value}"}, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@settings_bp.route("/update-session-info", methods=['POST'])
def update_info():
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')

        config.set_session_info(key, value)

        return {"success": True, "message": f"Updated {key} to {value}"}, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500

# Creating files and folders
@settings_bp.route("/create-file", methods=["POST"])
def create_file():
    try:
        data = request.get_json()
        path = data.get('path')
        content = data.get('content', '')

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            f.write(content)

        return {"success": True, "message": f"Created file {path}"}, 200

    except PermissionError:
        return {"success": False, "error": "Permission denied"}, 403
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@settings_bp.route("/create-directory", methods=["POST"])
def create_directory():
    try:
        data = request.get_json()
        path = data.get('path')

        os.makedirs(path, exist_ok=True)

        return {"success": True, "message": f"Created directory {path}"}, 200

    except PermissionError:
        return {"success": False, "error": "Permission denied"}, 403
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

# Renaming files and folders
@settings_bp.route("/rename-file", methods=["POST"])
def rename_file():
    try:
        data = request.get_json()

        old_path = data.get('oldPath')
        new_path = data.get('newPath')

        if not os.path.exists(old_path):
            return {"success": False, "error": f"File '{old_path}' not found"}, 404

        if os.path.exists(new_path):
            return {"success": False, "error": f"File '{new_path}' already exists"}, 409

        os.rename(old_path, new_path)
        return {"success": True, "message": f"Renamed to {new_path}"}, 200

    except PermissionError:
        return {"success": False, "error": "Permission denied"}, 403
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@settings_bp.route("/rename-folder", methods=["POST"])
def rename_folder():
    try:
        data = request.get_json()
        old_path = data.get('oldPath')
        new_path = data.get('newPath')

        if not os.path.exists(old_path):
            return {"success": False, "error": f"Folder '{old_path}' not found"}, 404

        if os.path.exists(new_path):
            return {"success": False, "error": f"Folder '{new_path}' already exists"}, 409

        os.rename(old_path, new_path)
        return {"success": True, "message": f"Renamed to {new_path}"}, 200

    except PermissionError:
        return {"success": False, "error": "Permission denied"}, 403
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

# Deleting files and folders
@settings_bp.route("/delete-file", methods=["DELETE"])
def delete_file():
    try:
        data = request.get_json()
        path = data.get('path')

        if not os.path.exists(path):
            return {"success": False, "error": f"File '{path}' not found"}, 404

        os.remove(path)
        return {"success": True, "message": f"Deleted file {path}"}, 200

    except PermissionError:
        return {"success": False, "error": "Permission denied"}, 403
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@settings_bp.route("/delete-directory", methods=["DELETE"])
def delete_directory():
    try:
        data = request.get_json()
        path = data.get('path')

        if not os.path.exists(path):
            return {"success": False, "error": f"Directory '{path}' not found"}, 404

        import shutil
        shutil.rmtree(path)
        return {"success": True, "message": f"Deleted directory {path}"}, 200

    except PermissionError:
        return {"success": False, "error": "Permission denied"}, 403
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

# Listing sessions
@settings_bp.route("/list-files")
def list_files():
    try:
        path = request.args.get('path', '')

        if not os.path.exists(path):
            return {"files": [], "error": f"Path '{path}' not found"}, 200

        if not os.path.isdir(path):
            return {"files": [], "error": f"Path '{path}' is not a directory"}, 200

        files = os.listdir(path)
        return {"files": files}, 200

    except PermissionError:
        return {"files": [], "error": "Permission denied"}, 403
    except Exception as e:
        return {"files": [], "error": str(e)}, 500

# Checking path validity
@settings_bp.route("/check-path")
def check_path():
    try:
        path = request.args.get('path', '')
        exists = os.path.exists(path)
        return {"exists": exists}, 200
    except Exception as e:
        return {"exists": False, "error": str(e)}, 500
