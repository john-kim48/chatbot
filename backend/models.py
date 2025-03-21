from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ARRAY, PickleType

db = SQLAlchemy()

class Documents(db.Model):
    __tablename__ = 'documents'
    document_name = db.Column(db.String, primary_key=True)
    document_content = db.Column(db.Text, nullable=False)

class FaissIndexStore(db.Model):
    __tablename__ = 'faiss_index_store'
    id = db.Column(db.Integer, primary_key=True)
    faiss_index = db.Column(PickleType, nullable=False)