from flask import Flask
from models import db
from routes import bot_bp, setup_db
from config import Config
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from models import FaissIndexStore

# Initialize Flask app and database
app = Flask(__name__)
app.config.from_object(Config) # need to change this to reflect environment in ms azure
CORS(app)
db.init_app(app)

# Initialize the SentenceTransformer model and FAISS index
app.model = SentenceTransformer('all-mpnet-base-v2')
print("Model loaded successfully.")

with app.app_context():
    db.create_all()
    index_data = FaissIndexStore.query.first()
    if index_data:
        index_array = np.frombuffer(index_data.faiss_index, dtype=np.uint8)
        app.index = faiss.deserialize_index(index_array)
        print("FAISS index loaded successfully.")
    else:
        print("No FAISS index found in the database.")
        app.index = None

# Register the Blueprint for the create_chat route
app.register_blueprint(bot_bp)
app.register_blueprint(setup_db)

if __name__ == '__main__':
    port = int(Config.PORT)
    app.run(host='0.0.0.0', port=port)
