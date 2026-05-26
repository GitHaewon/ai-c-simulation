"""Inspect ChromaDB current content — show all stored chunks and metadata."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()

import chromadb

client = chromadb.PersistentClient(path="./data/chroma")
collections = client.list_collections()
print(f"Collections: {[c.name for c in collections]}")

for col in collections:
    c = client.get_collection(col.name)
    total = c.count()
    print(f"\n[{col.name}] — {total} chunks total")
    if total == 0:
        print("  (empty)")
        continue
    sample = c.get(limit=total, include=["documents", "metadatas"])
    for i in range(len(sample["ids"])):
        meta = sample["metadatas"][i]
        text = sample["documents"][i][:100].replace("\n", " ")
        print(f"  [{sample['ids'][i][:10]}]")
        print(f"    source   : {meta.get('source_document','?')}")
        print(f"    deal_id  : {meta.get('deal_id','?')}")
        print(f"    section  : {meta.get('section','?')}")
        print(f"    date     : {meta.get('date','?')}")
        print(f"    text     : {text!r}")
