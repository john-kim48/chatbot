from flask import Flask
from models import db
from routes import bot_bp, setup_db, health_route
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

if __name__ == '__main__':
    port = int(Config.PORT)
    app.run(host='0.0.0.0', port=port)


# # routes.py
# from flask import Flask, request, jsonify, Blueprint, current_app
# from botbuilder.schema import Activity
# from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
# from botbuilder.core import TurnContext
# import asyncio

# from config import Config, BotConfig
# from models import Documents, db
# from openai_utils import get_conversational_chain

# # LangChain imports
# from langchain.embeddings import OpenAIEmbeddings
# from langchain.vectorstores import FAISS

# # Blueprints
# bot_bp = Blueprint("bot_bp", __name__)
# setup_db = Blueprint("setup_db", __name__)
# health_route = Blueprint("health_route", __name__)

# # Bot Framework setup
# config = BotConfig()
# adapter = CloudAdapter(ConfigurationBotFrameworkAuthentication(config))

# # in-memory store for chains, keyed by conversation ID
# convo_chains = {}


# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     # Initialize DB
#     db.init_app(app)

#     # Build or load FAISS index
#     with app.app_context():
#         docs = Documents.query.all()
#         texts = [doc.document_content for doc in docs]
#         metadatas = [{"source": doc.original_document_name} for doc in docs]

#         embeddings = OpenAIEmbeddings(openai_api_key=app.config['OPENAI_API_KEY'])
#         vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)

#         app.vectorstore = vectorstore

#     # Register blueprints
#     app.register_blueprint(bot_bp)
#     app.register_blueprint(setup_db, url_prefix='/')
#     app.register_blueprint(health_route, url_prefix='/')

#     return app


# async def on_message_activity(turn_context: TurnContext):
#     try:
#         conv_id = turn_context.activity.conversation.id
#         user_input = turn_context.activity.text or ""

#         # Initialize chain per conversation
#         if conv_id not in convo_chains:
#             convo_chains[conv_id] = get_conversational_chain(
#                 vectorstore=current_app.vectorstore,
#                 api_key=current_app.config['OPENAI_API_KEY'],
#                 k=5
#             )
#         chain = convo_chains[conv_id]

#         # Run the conversational chain
#         result = chain({'question': user_input})
#         answer = result.get('answer') or result.get('response')

#         # Send the answer back
#         await turn_context.send_activity(answer)

#     except Exception as e:
#         current_app.logger.error(f"Error in on_message_activity: {e}")
#         await turn_context.send_activity("An error occurred while processing your message.")


# @bot_bp.route("/api/messages", methods=["POST"])
# def messages():
#     try:
#         if "application/json" not in request.headers.get("Content-Type", ""):
#             return jsonify({"status": "Unsupported content type"}), 400

#         auth_header = request.headers.get("Authorization", "")
#         activity = Activity().deserialize(request.json)

#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         task = loop.create_task(adapter.process_activity(auth_header, activity, on_message_activity))
#         loop.run_until_complete(task)

#         return jsonify({"status": "ok"})
#     except Exception as e:
#         current_app.logger.error(f"Failed to process activity: {e}")
#         return jsonify({"error": str(e)}), 500


# @setup_db.route("/trigger-database-setup", methods=["POST"])
# def trigger_database_setup():
#     try:
#         secret = request.headers.get("X-Setup-Secret")
#         if secret != current_app.config['SETUP_SECRET']:
#             return jsonify({"error": "Unauthorized"}), 403

#         import runpy
#         runpy.run_path("reset.py")
#         runpy.run_path("setup_database.py")
#         return jsonify({"status": "success"}), 200

#     except Exception as e:
#         current_app.logger.error(f"Error in trigger_database_setup: {e}")
#         return jsonify({"error": str(e)}), 500


# @health_route.route("/health")
# def health():
#     return "ok", 200


# # openai_utils.py
# from langchain.llms import OpenAI
# from langchain.chains import ConversationalRetrievalChain
# from langchain.memory import ConversationBufferMemory

# # Factory to create a conversational retrieval chain
# def get_conversational_chain(vectorstore, api_key, k=5):
#     llm = OpenAI(api_key=api_key, model_name="gpt-4o-mini")
#     retriever = vectorstore.as_retriever(search_kwargs={"k": k})
#     memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

#     return ConversationalRetrievalChain(
#         llm=llm,
#         retriever=retriever,
#         memory=memory,
#         verbose=False,
#     )
