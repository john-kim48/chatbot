import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
from pdf2image import convert_from_path
import pytesseract
from sentence_transformers import SentenceTransformer
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from models import db, Documents, FaissIndexStore
import faiss
import numpy as np
import nltk

start_time = time.time()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base URL
base_url = "https://www.iqaluit.ca"
start_url = "https://www.iqaluit.ca/city-hall/city-council/bylaws2"

# Folder to save PDFs
pdf_folder = "/Users/johnkim/Desktop/bylaws_pdfs"
os.makedirs(pdf_folder, exist_ok=True)

all_pdf_links = set()
next_page_url = start_url  # Start with the first page

# Loop through pages until no "Next" button is found
while next_page_url:
    response = requests.get(next_page_url)

    # Parse the page
    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("a", href=True):
        pdf_href = link["href"].strip()  # Remove extra spaces
        if pdf_href.endswith(".pdf"):
            pdf_url = urljoin(base_url, pdf_href)
            all_pdf_links.add(pdf_url)

    # Find the "Next" button
    next_button = soup.find("li", class_="next")
    if next_button and next_button.find("a"):
        next_page_url = urljoin(base_url, next_button.find("a")["href"])
    else:
        next_page_url = None

# Download all PDFs
for pdf_url in all_pdf_links:
    pdf_name = os.path.join(pdf_folder, pdf_url.split("/")[-1])

    # Check if the PDF already exists
    if os.path.exists(pdf_name):
        continue

    try:
        pdf_response = requests.get(pdf_url, verify=False)
        if pdf_response.status_code == 200:
            with open(pdf_name, "wb") as pdf_file:
                pdf_file.write(pdf_response.content)
            print(f"Saved: {pdf_name}")
        else:
            print(f"Skipping (HTTP {pdf_response.status_code}): {pdf_url}")
    except Exception as e:
        print(f"Error downloading {pdf_url}: {e}")

def extract_text_from_pdfs(input_folder, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Iterate over all PDF files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            file_path = os.path.join(input_folder, filename)
            output_file_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}.txt")
            
            # Check if the .txt file already exists
            if os.path.exists(output_file_path):
                continue
            
            try:
                print(f"Processing {filename}...")
                # Convert PDF pages to images
                images = convert_from_path(file_path)
                
                # Extract text from each image
                text = ""
                for image in images:
                    text += pytesseract.image_to_string(image)
                
                # Save the extracted text to a .txt file
                with open(output_file_path, "w", encoding="utf-8") as txt_file:
                    txt_file.write(text)
                print(f"Extracted text from {filename} to {output_file_path}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

# Specify the input folder containing PDF files and the output folder for text files
txt_folder = "/Users/johnkim/Desktop/bylaws_txt"

# Extract text from PDFs and save as .txt files
extract_text_from_pdfs(pdf_folder, txt_folder)


def load_documents_from_folder(folder_path):
    documents = []
    document_names = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith(".txt"):  # Process .txt files
            with open(file_path, "r", encoding="utf-8") as f:
                documents.append(f.read())
                document_names.append(filename)
    return documents, document_names

# Specify the folder containing your text files
dataset_folder = "/Users/johnkim/Desktop/bylaws_txt"
documents, document_names = load_documents_from_folder(dataset_folder)

##########################################################################################################################################
##########################################################################################################################################

nltk.download('punkt')
nltk.download('punkt_tab')

model = SentenceTransformer('all-mpnet-base-v2')
print("downloaded nltk and model")#

def chunk_text(text, max_tokens):
    sentences = nltk.sent_tokenize(text)  # Split into sentences
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        token_count = len(sentence.split())  # Approximate token count
        if current_length + token_count > max_tokens:
            chunks.append(" ".join(current_chunk))  # Store completed chunk
            current_chunk = [sentence]  # Start new chunk
            current_length = token_count
        else:
            current_chunk.append(sentence)
            current_length += token_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))  # Add last chunk

    return chunks

def get_embeddings(documents, document_names, max_tokens):
    all_chunks = []
    chunk_doc_names = []
    for doc, doc_name in zip(documents, document_names):
        chunks = chunk_text(doc, max_tokens)
        all_chunks.extend(chunks)  # Store all chunks in a list
        for i in range(len(chunks)):
            chunk_doc_names.append(f"{doc_name}_{i}")
        # chunk_doc_names.extend([doc_name] * len(chunks))  # Add doc_name for each chunk

    # Embed all chunks
    embeddings = np.array([model.encode(chunk) for chunk in all_chunks], dtype=np.float32)
    return chunk_doc_names, all_chunks, embeddings  # Return both chunks and their embeddings

chunk_doc_names, all_chunks, document_embeddings = get_embeddings(documents, document_names, 256)

##########################################################################################################################################
##########################################################################################################################################

# Store embeddings in FAISS index
index = faiss.IndexFlatL2(document_embeddings.shape[1])
index.add(document_embeddings)
serialized_index = faiss.serialize_index(index)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Rycbar0408$@localhost/embeddings'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

n = 0
# Store embeddings in PostgreSQL
with app.app_context():
    db.create_all()

    for name, content in zip(chunk_doc_names, all_chunks):
        # Check if a document with the same name already exists.
        existing_doc = Documents.query.get(name)
        document = Documents(
                document_name=name,
                document_content=content,
            )
        db.session.add(document)
        n+=1

    faiss_index_store = FaissIndexStore.query.first()
    if faiss_index_store:
        faiss_index_store.faiss_index = serialized_index
        db.session.add(faiss_index_store)
    else:
        faiss_index_store = FaissIndexStore(faiss_index=serialized_index)
        db.session.add(faiss_index_store)
    
    db.session.commit()


end_time = time.time()
elapsed_time = end_time - start_time

print(f"Setup complete!: {n} documents in database. Time elapsed: {elapsed_time:.4f} seconds")