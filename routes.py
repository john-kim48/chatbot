from flask import request, jsonify, Blueprint, current_app
from models import Documents, Session, Message, db
from openai_utils import chat_search, filter_keywords
from botbuilder.schema import Activity
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.core import TurnContext
from config import Config, BotConfig
import runpy
import openai
import numpy as np
import asyncio

# Create a Blueprint for the create_chat route
bot_bp = Blueprint("bot_bp", __name__)
setup_db = Blueprint("setup_db", __name__)
health_route = Blueprint("health_route", __name__)

config = BotConfig()

adapter = CloudAdapter(ConfigurationBotFrameworkAuthentication(config))

openai_api_key = Config.OPENAI_API_KEY


def search(query):
    try:
        print("Running search...")
        if not current_app.index:
            print("No FAISS index found in app context.")
            return []

        document_data = Documents.query.all()
        print(f"Retrieved {len(document_data)} documents from DB.")
        
        document_content = [doc.document_content for doc in document_data]
        original_doc_name = [doc.original_document_name for doc in document_data]

        filtered_query = filter_keywords(query)
        print(f"Filtered query: {filtered_query}")

        response = openai.Embedding.create(
            input=filtered_query,
            model="text-embedding-3-large"
        )
   
        query_embedding = np.array(response.data[0].embedding, dtype=np.float32).reshape(1, -1)

        distances, indices = current_app.index.search(query_embedding, 250)
        print(f"Search complete. Top match indices: {indices[0]}")

        output_document_data = []
        output_document_names = []
        original_doc_name_list = [original_doc_name[i] for i in indices[0]]

        for name in original_doc_name_list:
            if name not in output_document_names:
                output_document_names.append(name)

        for name in output_document_names:
            indexes = [i for i, val in enumerate(original_doc_name_list) if val == name]
            content = ''.join([document_content[i] for i in indexes])
            output_document_data.append(content)

        print(f"Returning {len(output_document_data)} document chunks.")
        return list(zip(output_document_data, output_document_names))

    except Exception as e:
        print(f"[search] Exception occurred: {e}")
        return []


async def on_message_activity(turn_context: TurnContext):
    try:
        query = turn_context.activity.text.strip() if turn_context.activity.text else ""
        print(f"Received message: {query}")
        context = search(query)
        response_text = chat_search(query, context)
        await turn_context.send_activity(response_text)
        print("Response sent to user.")
    except Exception as e:
        print(f"[on_message_activity] Exception: {e}")
        await turn_context.send_activity("An error occurred while processing your message.")


@bot_bp.route("/api/messages", methods=["POST"])
def messages():
    try:
        print("Received POST to /api/messages")

        if "application/json" not in request.headers.get("Content-Type", ""):
            print("Unsupported content type.")
            return jsonify({"status": "Unsupported content type"}), 400
        
        auth_header = request.headers.get("Authorization", "")
        activity = Activity().deserialize(request.json)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(adapter.process_activity(auth_header, activity, on_message_activity))
        loop.run_until_complete(task)

        print("Processed activity successfully.")
        return jsonify({"status": "ok"})

    except Exception as e:
        ###
        auth_header = request.headers.get("Authorization", "")
        activity = Activity().deserialize(request.json)
        print(f"Failed to process activity: {auth_header}")
        ###
        print(f"[messages] Exception: {e}")
        return jsonify({"error": str(e)}), 500


@setup_db.route("/trigger-database-setup", methods=["POST"])
def trigger_database_setup():
    try:
        print("Triggering database setup...")
        secret = request.headers.get("X-Setup-Secret")
        if secret != Config.SETUP_SECRET:
            print("Unauthorized setup attempt.")
            return jsonify({"error": "Unauthorized"}), 403

        runpy.run_path("reset.py")
        print("Ran reset.py")
        runpy.run_path("setup_database.py")
        print("Ran setup_database.py")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"[trigger_database_setup] Exception: {e}")
        return jsonify({"error": str(e)}), 500
    
@health_route.route("/health")
def health():
    return "ok", 200