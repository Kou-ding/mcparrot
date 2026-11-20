import asyncio
import json
import os
import queue
import threading
import uuid

from dotenv import load_dotenv
from flask import Blueprint, Response, request

from mcparrot.core.client import MyClient
from mcparrot.utils import config

load_dotenv()

chat_bp = Blueprint('chat', __name__)

_SENTINEL = object()

client = MyClient(api_key=os.getenv("API_KEY"),
                base_url=os.getenv("BASE_URL"))

# Dictionary to store active tasks for cancellation
active_tasks = {}

@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "")

    if not user_message.strip():
        return {"error": "Empty message"}, 400

    event_queue = queue.Queue()

    # Unique ID to track this specific request's background task
    request_id = str(uuid.uuid4())

    def worker():
        # Create a dedicated event loop for this background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def runner():
            try:
                current_mode = config.get_setting("mode")
                if current_mode == "hawk":
                    async for event in client.hawk_query(user_message):
                        event_queue.put(event)
                elif current_mode == "raven":
                    async for event in client.raven_query(user_message):
                        event_queue.put(event)
            except asyncio.CancelledError:
                # Catch the cancellation signal and notify frontend
                event_queue.put({"type": "error", "message": "Request cancelled by user"})
            except Exception as e:
                event_queue.put({"type": "error", "message": str(e)})
            finally:
                event_queue.put(_SENTINEL)

        # Create task and store it for cancellation
        task = loop.create_task(runner())
        active_tasks[request_id] = (task, loop)

        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
        finally:
            active_tasks.pop(request_id, None)
            loop.close()

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        try:
            # Catch client disconnection
            while True:
                item = event_queue.get()
                if item is _SENTINEL:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        except GeneratorExit:
            # Client disconnected (frontend aborted). Cancel the background task.
            task_info = active_tasks.get(request_id)
            if task_info:
                task, loop = task_info
                if not task.done():
                    loop.call_soon_threadsafe(task.cancel)
            raise

    return Response(generate(), mimetype="text/event-stream")
