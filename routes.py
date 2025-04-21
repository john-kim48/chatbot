from flask import request, jsonify, Blueprint, current_app
from models import Documents, Session, Message, db
from openai_utils import chat_search, filter_keywords
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from config import Config
import runpy

# Create a Blueprint for the create_chat route
bot_bp = Blueprint("bot_bp", __name__)
setup_db = Blueprint("setup_db", __name__)

bot_adapter_settings = BotFrameworkAdapterSettings(
    app_id=Config.CLIENT_ID,
    app_password=Config.CLIENT_SECRET # might need to change this to AZURE_CLIENT_SECRET (why?)
    # app_password=Config.AZURE_CLIENT_SECRET
) # this needs to be renewed every 2 years -.-
adapter = BotFrameworkAdapter(bot_adapter_settings)

def search(query):
    """
    Search for documents using the FAISS index and the pre-initialized model.
    """
    if not current_app.model or not current_app.index:
        return []

    document_data = Documents.query.all()
    document_content = [document.document_content for document in document_data]
    original_doc_name = [document.original_document_name for document in document_data]

    # Filter keywords out of the query
    filtered_query = filter_keywords(query)

    # Encode the query and search the FAISS index
    query_embedding = current_app.model.encode(filtered_query).reshape(1, -1)

    # if i have time:
    # encode each word in the query and then search based on each word
    # filter each word individually and then use all indices.

    distances, indices = current_app.index.search(query_embedding, 50)

    output_document_data = []
    output_document_names = []
    original_doc_name_list = [original_doc_name[i] for i in indices[0]]

    for name in original_doc_name_list:
        if name in output_document_names:
            continue
        else:
            output_document_names.append(name)
    
    for name in output_document_names:
        document_content_placeholder = ""
        indexes = []
        for i in range(len(original_doc_name_list)):
            if original_doc_name_list[i] == name:
                indexes.append(i)
        for index in indexes:
            document_content_placeholder += document_content[index]
        output_document_data.append(document_content_placeholder)

    return [(doc, name) for doc, name in zip(output_document_data, output_document_names)]

async def on_message_activity(turn_context: TurnContext):
    # Extract the user's message
    query = turn_context.activity.text.strip() if turn_context.activity.text else ""
    # Search using user query
    context = search(query)
    response_text = chat_search(query, context)
    # Send back the generated response
    await turn_context.send_activity(response_text)

@bot_bp.route("/api/messages", methods=["POST"])
def messages():
    if "application/json" in request.headers.get("Content-Type", ""):
        activity = Activity().deserialize(request.json)
        # Create and set an event loop for async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(adapter.process_activity(activity, "", on_message_activity))
        loop.run_until_complete(task)
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "Unsupported content type"}), 400
    

@setup_db.route("/trigger-database-setup", methods=["POST"])
def trigger_database_setup():
    secret = request.headers.get("X-Setup-Secret")
    if secret != Config.SETUP_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        runpy.run_path("reset.py")
        runpy.run_path("setup_database.py")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500