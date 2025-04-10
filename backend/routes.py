from flask import request, jsonify, Blueprint, current_app
from models import Documents
from openai_utils import chat_search, filter_keywords
import re
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

# Create a Blueprint for the create_chat route
create_chat_bp = Blueprint('create_chat', __name__)
bot_bp = Blueprint("bot_bp", __name__)

bot_adapter_settings = BotFrameworkAdapterSettings(
    app_id="YOUR_APP_ID",           # Your Azure Bot Service App ID
    app_password="YOUR_APP_PASSWORD"  # Your Azure Bot Service App Password
)
adapter = BotFrameworkAdapter(bot_adapter_settings)

def search(query):
    """
    Search for documents using the FAISS index and the pre-initialized model.
    """
    if not current_app.model or not current_app.index:
        return []  # Handle case where model or index is not loaded

    document_data = Documents.query.all()
    document_names = [document.document_name for document in document_data]
    document_content = [document.document_content for document in document_data]
    original_doc_name = [document.original_document_name for document in document_data]

    # filtering the keywords out of the query
    filtered_query = filter_keywords(query)

    # Encode the query and search the FAISS index
    query_embedding = current_app.model.encode(filtered_query).reshape(1, -1) # encode each word in the query and then search based on each word

    distances, indices = current_app.index.search(query_embedding, 50) # filter each word individually and then use all indices.

    output_document_data = []
    output_document_names = []
    document_names_list = [document_names[i] for i in indices[0]]
    document_content_list = [document_content[i] for i in indices[0]]
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

    print(len(output_document_names))

    return [(doc, name) for doc, name in zip(output_document_data, output_document_names)]

@create_chat_bp.route('/create-chat', methods=['POST'])
def create_chat():
    """
    Handle the create-chat endpoint.
    """
    if not current_app.model or not current_app.index:
        return jsonify({"error": "Model or index not loaded"}), 500

    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Perform the search and generate a response
    context = search(query)
    created_chat = chat_search(query, context)

    return jsonify({"response": created_chat}), 200

async def on_message_activity(turn_context: TurnContext):
    # Extract the user's message
    user_text = turn_context.activity.text.strip() if turn_context.activity.text else ""
    # Process the message using your custom logic
    context = search(user_text)
    response_text = chat_search(user_text, context)
    # Send back the processed message
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
