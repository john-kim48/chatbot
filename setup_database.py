import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
from pdf2image import convert_from_bytes
import pytesseract
from flask import Flask
from models import db, Documents, FaissIndexStore
import faiss
import numpy as np
import nltk
from config import Config
from msal import ConfidentialClientApplication
import openai
from openai_utils import document_keywords

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TENANT_ID       = Config.AZURE_TENANT_ID
CLIENT_ID       = Config.CLIENT_ID
CLIENT_SECRET   = Config.AZURE_CLIENT_SECRET
SCOPE           = ["https://graph.microsoft.com/.default"]
SITE_ID         = Config.SHAREPOINT_SITE_ID
LIBRARY_PDF     = "bylaws_pdf"
LIBRARY_TXT     = "bylaws_txt"
CHUNK_SIZE      = 5 * 1024 * 1024  # 5MB chunks

# Initialize MSAL client
msal_app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET
)


def get_access_token():
    token = msal_app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in token:
        raise RuntimeError(f"Token error: {token.get('error_description')}")
    return token["access_token"]


def graph_headers():
    return {"Authorization": f"Bearer {get_access_token()}"}


def get_drive_id(name):
    url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives"
    resp = requests.get(url, headers=graph_headers())
    resp.raise_for_status()
    for d in resp.json().get("value", []):
        if d.get("name") == name:
            return d["id"]
    raise ValueError(f"Drive {name} not found")


def file_exists(drive_id, filename):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    resp = requests.get(url, headers=graph_headers())
    resp.raise_for_status()
    return any(item["name"].lower() == filename.lower() for item in resp.json().get("value", []))


def create_upload_session(drive_id, target_path):
    url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
        f"/root:/{requests.utils.quote(target_path, safe='')}:/createUploadSession"
    )
    body = {"item": {"@microsoft.graph.conflictBehavior": "replace", "name": target_path.split('/')[-1]}}
    resp = requests.post(url, headers={**graph_headers(), "Content-Type": "application/json"}, json=body)
    resp.raise_for_status()
    return resp.json()["uploadUrl"]


def upload_bytes(drive_id, target_path, data_bytes):
    if file_exists(drive_id, target_path):
        print(f"Skipping existing file: {target_path}")
        return

    size = len(data_bytes)
    if size <= 4 * 1024 * 1024:
        # simple PUT
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}"  
            f"/root:/{requests.utils.quote(target_path, safe='')}:/content"
        )
        resp = requests.put(url, headers=graph_headers(), data=data_bytes)
        resp.raise_for_status()
    else:
        upload_url = create_upload_session(drive_id, target_path)
        for start in range(0, size, CHUNK_SIZE):
            end = min(start + CHUNK_SIZE, size) - 1
            chunk = data_bytes[start:end+1]
            headers = {
                "Content-Range": f"bytes {start}-{end}/{size}",
                "Content-Length": str(len(chunk))
            }
            r = requests.put(upload_url, headers=headers, data=chunk)
            if r.status_code not in (200, 201, 202):
                raise RuntimeError(f"Chunk upload failed: {r.text}")


def extract_text(pdf_bytes):
    pages = convert_from_bytes(pdf_bytes)
    return "".join(pytesseract.image_to_string(page) for page in pages)


# def run_pipeline():
#     pdf_drive = get_drive_id(LIBRARY_PDF)
#     txt_drive = get_drive_id(LIBRARY_TXT)

#     # Scraping setup
#     base = "https://www.iqaluit.ca"
#     next_page = "https://www.iqaluit.ca/city-hall/city-council/bylaws2"
#     pdf_links = set()  # will store tuples of (url, filename)

#     # Collect PDF links along with custom filenames from the /content/ slug
#     while next_page:
#         resp = requests.get(next_page, verify=False)
#         resp.raise_for_status()
#         soup = BeautifulSoup(resp.text, 'html.parser')

#         for row in soup.select('tr'):
#             page_link = row.select_one('div.title a[href]')
#             download_link = row.select_one('div.download a[href$=".pdf"]')
#             if not page_link or not download_link:
#                 continue

#             # Extract slug after '/content/' from the page URL
#             slug = page_link['href'].split('/content/')[-1]
#             filename = f"{slug}.pdf"

#             # Full URL of the PDF
#             pdf_url = urljoin(base, download_link['href'])
#             pdf_links.add((pdf_url, filename))

#         # Find next page
#         nxt = soup.select_one("li.next a[href]")
#         next_page = urljoin(base, nxt['href']) if nxt else None

#     # Process each PDF
#     for url, filename in pdf_links:
#         txt_name = filename.rsplit('.', 1)[0] + '.txt'

#         # Skip if both PDF and TXT already exist
#         if file_exists(pdf_drive, filename) and file_exists(txt_drive, txt_name):
#             print(f"Skipping {filename} (already uploaded)")
#             continue

#         # Download PDF
#         resp = requests.get(url, verify=False)
#         resp.raise_for_status()
#         pdf_data = resp.content

#         # Upload PDF
#         upload_bytes(pdf_drive, filename, pdf_data)

#         # Extract and upload text
#         text = extract_text(pdf_data)
#         upload_bytes(txt_drive, txt_name, text.encode('utf-8'))

#     print("Pipeline completed successfully.")

print("Starting pipeline...")
# if __name__ == '__main__':
#     run_pipeline()


def load_documents_from_sharepoint_txt():
    txt_drive_id = get_drive_id(LIBRARY_TXT)
    headers = graph_headers()
    documents = []
    document_names = []

    # List files in the TXT library
    url = f"https://graph.microsoft.com/v1.0/drives/{txt_drive_id}/root/children"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    items = resp.json().get("value", [])

    for item in items:
        if item["name"].endswith(".txt"):
            download_url = f"https://graph.microsoft.com/v1.0/drives/{txt_drive_id}/items/{item['id']}/content"
            file_resp = requests.get(download_url, headers=headers)
            file_resp.raise_for_status()
            documents.append(file_resp.text)
            document_names.append(item["name"])

    return documents, document_names

documents, document_names = load_documents_from_sharepoint_txt()
print("finished loading documents")


nltk.download('punkt')
nltk.download('punkt_tab')

model = "text-embedding-3-large"
print("downloaded nltk and model")


def get_embeddings(documents, document_names, batch_size):
    all_keywords = []
    doc_names = []
    original_doc_names = []

    for doc, doc_name in zip(documents, document_names):
        keywords = document_keywords(doc)

        # Clean and split the keyword string into a list
        keyword_list = [k.strip() for k in keywords.split(",") if isinstance(k, str) and k.strip()]

        # Extend the global lists
        all_keywords.extend(keyword_list)
        doc_names.extend([f"{doc_name}_{i+1}" for i in range(len((keyword_list)))])
        original_doc_names.extend([doc_name] * len(keyword_list))

    embeddings = []

    # Batch embedding requests
    for i in range(0, len(all_keywords), batch_size):
        batch = all_keywords[i:i + batch_size]

        # Validate input before sending to OpenAI
        if not all(isinstance(k, str) and k.strip() for k in batch):
            raise ValueError(f"Invalid input in batch {i}: {batch}")

        response = openai.Embedding.create(
            input=batch,
            model=model
        )

        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)

    embeddings = np.array(embeddings, dtype=np.float32)
    print("Embeddings shape:", embeddings.shape)

    return embeddings, doc_names, all_keywords, original_doc_names

document_embeddings, document_names_numbered, keyword_list, original_doc_names = get_embeddings(documents, document_names, 500)


# Store embeddings in FAISS index
index = faiss.IndexFlatL2(document_embeddings.shape[1])
index.add(document_embeddings)
serialized_index = faiss.serialize_index(index)


app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Store embeddings in PostgreSQL
with app.app_context():
    db.create_all()
    for keyword, name in zip(keyword_list, document_names_numbered):
        existing_doc = Documents.query.get(name)
        document = Documents(
                document_name=name,
                document_content = documents[document_names.index(name[:name.rfind('_')] if name.split('_')[-1].isdigit() else name)],
                document_keywords=keyword,
                original_document_name=original_doc_names[keyword_list.index(keyword)] if keyword in original_doc_names else name
            )
        db.session.add(document)

    faiss_index_store = FaissIndexStore.query.first()
    if faiss_index_store:
        faiss_index_store.faiss_index = serialized_index
        db.session.add(faiss_index_store)
    else:
        faiss_index_store = FaissIndexStore(faiss_index=serialized_index)
        db.session.add(faiss_index_store)

    db.session.commit()