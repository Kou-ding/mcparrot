import asyncio
import json
import os
import queue
import threading

from dotenv import load_dotenv
from flask import Blueprint, Response, request

from mcparrot.core.client import MyClient
from mcparrot.utils import config

load_dotenv()

chat_bp = Blueprint('chat', __name__)

_SENTINEL = object()

client = MyClient(api_key=os.getenv("API_KEY"),
                base_url=os.getenv("BASE_URL"))

@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "")

    if not user_message.strip():
        return {"error": "Empty message"}, 400

    event_queue: queue.Queue = queue.Queue()

    current_mode = config.get_setting("mode")

    def worker():
        async def runner():
            try:
                if current_mode == "hawk":
                    async for event in client.hawk_query(user_message):
                        event_queue.put(event)
                if current_mode == "raven":
                    async for event in client.raven_query(user_message):
                        event_queue.put(event)
            except Exception as e:
                event_queue.put({"type": "error", "message": str(e)})
            finally:
                event_queue.put(_SENTINEL)

        asyncio.run(runner())

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            item = event_queue.get()
            if item is _SENTINEL:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return Response(generate(), mimetype="text/event-stream")
