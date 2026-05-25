import os
import re
import pypdf
from sentence_transformers import SentenceTransformer
import chromadb
from config import VECTOR_STORE_DIR, DATA_DIR

# 1. Initialize the SentenceTransformer Embedding Model (matching your technique)
print("Initializing sentence-transformers Model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# 1.5. Clean reset the database folder to resolve incompatible/corrupted SQLite schemas under Python 3.13
import shutil
backup_path = VECTOR_STORE_DIR + "_backup"
if os.path.exists(VECTOR_STORE_DIR):
    print("Detected existing ChromaDB directory. Backing up and clearing to ensure a fresh, Python 3.13 compatible database schema...")
    try:
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
        shutil.move(VECTOR_STORE_DIR, backup_path)
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        print("Successfully cleared old database files. Re-initializing client...")
    except Exception as e:
        print(f"Warning: Could not automatically clear database folder: {e}. Trying to proceed...")

# 2. Initialize Persistent ChromaDB Client pointing to config directory (data/chroma_db)
print(f"Initializing Persistent ChromaDB Client at: {VECTOR_STORE_DIR}")
client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)

# 3. Create or get the exact collection name
collection_name = "customer_support_guide"
print(f"Retrieving or creating collection: '{collection_name}'")
collection = client.get_or_create_collection(name=collection_name)

# 4. Map your metadata categories to the exact local filenames in the project root
pdf_mapping = {
    "Service_outage": "PDF2_Service_Outage_Guide 2.pdf",
    "Network_connectivity": "PDF1_Network_Connectivity_Guide 2.pdf",
    "Hardware_equipment": "PDF3_Hardware_Equipment_Guide 2.pdf",
    "Customer_experience": "PDF4_Customer_Experience_Guide 2.pdf"
}

# 5. Helper functions to chunk text based on headings

def is_heading(line: str) -> bool:
    """Detect main section headings from extracted PDF text.
    
    True headings are numbered issues/sections like:
    - "1. Signal Loss / Weak Coverage"
    - "2. Internet Not Working (Fiber)"
    
    NOT headings (content within sections):
    - "Step 1:", "Step 2:" etc.
    - Table headers or sub-guides
    """
    candidate = line.strip()
    if not candidate:
        return False
    if len(candidate) > 200:
        return False

    # EXCLUDE lines that are steps (Step 1:, Step 2:, etc.) — these are NOT headings
    if re.match(r'^Step\s+\d+[:\.)]?\s+', candidate, re.IGNORECASE):
        return False

    # MAIN PATTERN: Numbered section headings like "1. Issue Title" or "2.1. Sub-topic"
    # This is the primary indicator of a true heading in these PDFs
    if re.match(r'^\d+(?:\.\d+)*\.\s+.{5,}', candidate):
        return True

    # Uppercase section titles (but not single words)
    if candidate.isupper() and len(candidate.split()) >= 3 and len(candidate) > 10:
        return True

    # Short lines ending with colon, but exclude step-like patterns
    if candidate.endswith(':') and not re.match(r'^\w+\s+\d+\s*$', candidate):
        # This is too permissive, only keep if it looks like a heading keyword
        heading_keywords = ['guide', 'problem', 'issue', 'failure']
        if any(kw in candidate.lower() for kw in heading_keywords):
            return True

    return False


def split_section_to_subchunks(section_lines, max_chunk_chars=1200):
    """Split a very large heading section into subchunks without breaking steps mid-way."""
    section_text = "\n".join(section_lines).strip()
    if len(section_text) <= max_chunk_chars:
        return [section_text]

    subchunks = []
    current = []
    current_size = 0

    for line in section_lines:
        line_size = len(line) + 1
        is_boundary = bool(re.match(r'^\s*(?:\d+\.|\d+\)|Step\s+\d+|[-*•])\s+', line, re.IGNORECASE))

        if current and current_size + line_size > max_chunk_chars and is_boundary:
            subchunks.append("\n".join(current).strip())
            current = [line]
            current_size = line_size
        else:
            current.append(line)
            current_size += line_size

    if current:
        subchunks.append("\n".join(current).strip())

    return subchunks


def chunk_by_headings(text):
    """Chunk text by detected headings and preserve each heading section as a semantic chunk."""
    lines = text.splitlines()
    chunks = []
    current = []

    for line in lines:
        if is_heading(line) and current:
            chunks.extend(split_section_to_subchunks(current))
            current = [line]
        else:
            current.append(line)

    if current:
        chunks.extend(split_section_to_subchunks(current))

    return [chunk.strip() for chunk in chunks if chunk.strip()]


# 6. Helper function to extract text from a PDF (using modern pypdf which is already installed!)
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text.strip() + "\n"
    except FileNotFoundError:
        print(f"[ERROR] PDF File not found -> '{pdf_path}'. Please ensure it is in the project root directory.")
    return text

# 7. Process each PDF and store in ChromaDB
for category, filename in pdf_mapping.items():
    pdf_path = os.path.join(os.path.dirname(__file__) or ".", filename)
    print(f"\nProcessing '{filename}' for category: '{category}'...")
    
    # Extract
    raw_text = extract_text_from_pdf(pdf_path)
    
    if not raw_text:
        continue # Skip if file was not found or is empty
        
    # Chunk by heading sections
    text_chunks = chunk_by_headings(raw_text)
    
    # Embed and Store
    for i, chunk in enumerate(text_chunks):
        embedding = model.encode(chunk).tolist()
        heading = chunk.splitlines()[0].strip() if chunk.splitlines() else category
        
        # Store in vector DB with metadata for category and heading
        collection.add(
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"category": category, "heading": heading}],
            ids=[f"{category}_chunk_{i}"]
        )
    print(f"  -> Successfully stored {len(text_chunks)} heading-based chunks into ChromaDB collection '{collection_name}'.")

print("\n[SUCCESS] All PDFs successfully processed and stored in your local ChromaDB vector store!")

# 8. Test Query (Verifying your filtered search works perfectly!)
print("\n" + "=" * 60)
print("TESTING LOCAL QUERY RETRIEVAL:")
print("=" * 60)
test_query = "What do I do if the router light is red?"
query_vector = model.encode(test_query).tolist()

results = collection.query(
    query_embeddings=[query_vector],
    n_results=2,
    where={"category": "Hardware_equipment"} # Filters search strictly within the Hardware PDF
)

print(f"Query:                    '{test_query}'")
print(f"Filtered Search Category: 'Hardware_equipment'\n")
print("Results retrieved:")
if results and results.get('documents') and len(results['documents']) > 0:
    for idx, doc in enumerate(results['documents'][0]):
        metadata = results.get('metadatas', [[{}]])[0][idx] if results.get('metadatas') else {}
        heading = metadata.get('heading', 'Unknown heading')
        doc_lines = doc.splitlines()
        if doc_lines and doc_lines[0].strip() == heading:
            body = "\n".join(doc_lines[1:]).strip()
        else:
            body = doc
        print(f"Result {idx + 1} - Heading: {heading}\n{body}\n")
else:
    print("No matching records found.")
print("=" * 60 + "\n")
