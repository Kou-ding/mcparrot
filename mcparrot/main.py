import asyncio
import json
import os
import queue
import threading

from core.client import Client
from dotenv import load_dotenv
from flask import Flask, Response, render_template, request
from flask_cors import CORS

load_dotenv()

# Base directory one up from src/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, 'static')
            )
CORS(app)

client = Client(
    api_key=API_KEY,
    base_url=BASE_URL
)

_SENTINEL = object()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "")

    if not user_message.strip():
        return {"error": "Empty message"}, 400

    event_queue: "queue.Queue" = queue.Queue()

    def worker():
        async def runner():
            try:
                async for event in client.stream_query(user_message):
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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
