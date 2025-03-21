from flask import request, jsonify, Blueprint, current_app
from models import Documents
from openai_utils import chat_search, filter_keywords
import re

# Create a Blueprint for the create_chat route
create_chat_bp = Blueprint('create_chat', __name__)

def search(query):
    """
    Search for documents using the FAISS index and the pre-initialized model.
    """
    if not current_app.model or not current_app.index:
        return []  # Handle case where model or index is not loaded

    document_data = Documents.query.all()
    document_names = [document.document_name for document in document_data]
    document_content = [document.document_content for document in document_data]

    # filtering the keywords out of the query
    # filtered_query = filter_keywords(query)

    # Encode the query and search the FAISS index
    query_embedding = current_app.model.encode(query).reshape(1, -1) # encode each word in the query and then search based on each word

    distances, indices = current_app.index.search(query_embedding, 6) # filter each word individually and then use all indices.

    document_content_total = []
    document_names_list = [document_names[i] for i in indices[0]]

    # removing the _1, _2, _3, etc. from the document names
    document_names_cleaned = [re.sub(r'_\d+$', '', s) for s in document_names_list]

    for name in document_names_cleaned:
        document_content_recombined = ''
        for i in range(len(document_names)):
            if name == re.sub(r'_\d+$', '', document_names[i]):
                document_content_recombined += document_content[i]
        document_content_total.append(document_content_recombined) # this is not working properly, need to fix
    
    # i need to return something else, the actual document names and actual documents
    return [(doc, name) for doc, name in zip(document_content_recombined, document_names_cleaned)] # total and cleaned


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
    for doc_content, doc_name in context:
        print(doc_name)
    created_chat = chat_search(query, context)

    return jsonify({"response": created_chat}), 200