from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import PickleType
from datetime import datetime

db = SQLAlchemy()

class Documents(db.Model):
    __tablename__ = 'documents'
    document_name = db.Column(db.String, primary_key=True)
    document_content = db.Column(db.Text, nullable=False)

class FaissIndexStore(db.Model):
    __tablename__ = 'faiss_index_store'
    id = db.Column(db.Integer, primary_key=True)
    faiss_index = db.Column(PickleType, nullable=False)

# session stuff:
class Session(db.Model):
    __tablename__ = 'sessions'
    session_id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('sessions.session_id', ondelete='CASCADE'))
    sender = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)