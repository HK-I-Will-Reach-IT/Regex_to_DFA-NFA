from flask import Flask
from flask_cors import CORS
from controllers.automata_controller import automata_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(automata_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=True, port=5000)