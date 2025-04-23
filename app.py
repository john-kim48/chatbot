from flask import Flask
from models import db
from routes import bot_bp, setup_db, health_route, pingpong
from config import Config
from flask_cors import CORS
import numpy as np
import faiss
from models import FaissIndexStore

# Initialize Flask app and database
app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db.init_app(app)

print("app starting")

with app.app_context():
    db.create_all()
    index_data = FaissIndexStore.query.first()
    if index_data:
        index_array = np.frombuffer(index_data.faiss_index, dtype=np.uint8)
        app.index = faiss.deserialize_index(index_array)
        print(f"FAISS index loaded")
    else:
        print("No FAISS index found in the database.")
        app.index = None

# Register the Blueprint for the create_chat route
app.register_blueprint(bot_bp)
app.register_blueprint(setup_db)
app.register_blueprint(health_route)
app.register_blueprint(pingpong)

if __name__ == '__main__':
    port = int(Config.PORT)
    app.run(host='0.0.0.0', port=port)