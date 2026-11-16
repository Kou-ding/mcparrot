from flask import Flask, render_template
from flask_cors import CORS

# Routes
from mcparrot.routes.chat import chat_bp
from mcparrot.routes.sessions import sessions_bp
from mcparrot.routes.settings import settings_bp

app = Flask(__name__,
            template_folder="templates",
            static_folder="static",
            )
CORS(app)

# Blueprints
app.register_blueprint(chat_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(settings_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 4242
    print(f"Running on: http://{host}:{port}")
    app.run(debug=False, host=host, port=port)
