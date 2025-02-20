import sys
import os
import re

from enum import auto, Enum
from pathlib import Path
from typing import Optional
from pprint import pprint
import hashlib
import json

import chromadb
from chromadb.utils import embedding_functions
from chromadb import Collection
from chromadb.api import ClientAPI

from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# Exported functions:
__all__ = [
    "ensure_collection",
    "insert_document",
    "load_files_from_md_directory_tree",
]

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")

ALL_COLLECTION_NAME = "All_Topics"
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on, strip_headers=False)
recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=1500)


class CollectionStatus(Enum):
    COLLECTION_CREATED = auto()
    COLLECTION_EXISTS = auto()
    COLLECTION_CREATION_FAILED = auto()


def ensure_collection(client: chromadb.ClientAPI, collection_name: str) -> tuple[str, Optional[Collection]]:
    try:
        # Check if the collection already exists
        collection = client.get_collection(name=collection_name, embedding_function=sentence_transformer_ef)
        print(f"Collection '{collection_name}' already exists.")
        return "COLLECTION_EXISTS", collection
    except Exception:
        # If it doesn't exist, create a new collection
        try:
            collection = client.create_collection(name=collection_name, embedding_function=sentence_transformer_ef)
            print(f"Collection '{collection_name}' created successfully.")
            return "COLLECTION_CREATED", collection
        except Exception as e:
            print(f"Failed to create collection '{collection_name}': {e}")
            return "COLLECTION_CREATION_FAILED", None


def clean_text(raw_text: str) -> str:
    # Clean up the text to remove extra spaces and line breaks
    cleaned_text = raw_text.replace("\n", " ")
    cleaned_text = re.sub(r"\s+", " ", raw_text)
    return cleaned_text

## This is Character Splitting. Not optimal
#def get_chunks(text: str, max_words: int = 150) -> list[tuple[str, int]]:
#    words = clean_text(text).split(" ")
#    chunks = []
    # Split the text into chunks of max_words length
#    for i in range(0, len(words), max_words):
#        chunk = words[i:i + max_words]
#        chunk_text = " ".join(chunk).strip()
#        chunks.append((chunk_text, i // max_words))
#    return chunks


def document_path_get_id_prefix(doc_path: Path) -> str:
    """returns the id prefix as used to prefix all chunks in chromaDB from the document path

    :param doc_path: The path to the document.
    :returns: the id string.
    """
    return doc_path.stem.replace(" ", "-").replace("_", "-")


def insert_document(document_path: Path, collection: Collection, hash: Optional[str] = None) -> None:
    """
    Reads a markdown file, splits it into chunks, generates embeddings,
    and inserts the chunks into a ChromaDB collection.
    """
    # Read the markdown file content
    with open(document_path, 'r') as file:
        markdown_content = file.read()
    
    #markdown_content = clean_text(markdown_content)

    text = splitter.split_text(markdown_content)    
    
    document_name = document_path_get_id_prefix(document_path)

    # Get chunks of text from the markdown content
    #chunks = get_chunks(markdown_content)
    document_chunks = []
    document_ids = []

    #print("Whole text")
    #print(text)
    for chunk_index, chunk in enumerate(text):

        document_ids.append(f"{document_name}_chunk{chunk_index}")
        document_chunks.append(chunk.page_content)

    
    collection.add(
                documents=document_chunks,
                ids=document_ids,
                metadatas=[{"filename": document_path.name}] * len(document_ids)
            )
    
    if hash:
        # also add hash information into db for change detection
        _update_file_hash(collection, document_path, hash)
        
    '''
    print("Adding chunks to collection:")
    #print(document_chunks)

    # Add documents with embeddings to the ChromaDB collection
    batch_size = len(document_chunks) // 100  # Calculate 10% of chunks
    if batch_size == 0:  # Handle small input where 10% is less than 1
        batch_size = 1

    # Iterate through document_chunks in batches
    for i in range(0, len(document_chunks), batch_size):
        batch_chunks = document_chunks[i:i + batch_size]
        batch_ids = document_ids[i:i + batch_size]
        print(batch_ids)

        print(f"Before batch {i}, Memory Usage: {psutil.virtual_memory().percent}%")
        try:
            collection.add(
                documents=batch_chunks,
                ids=batch_ids
            )
        except Exception as e:
            print(f"Error occurred: {e}")
        print(f"After batch {i}, Memory Usage: {psutil.virtual_memory().percent}%")
'''


def delete_document(document_path: Path, collection: Collection) -> None:
    """Delete all chunks belonging to the document located at the document_path from the collection.

    the file will not be opened or loaded from the disk in the process.

    :param document_path: The path to the document to delete (does not have to be still existend on disk)
    :param collection: The collection to delete the document from
    """
    collection.delete(where={'filename': document_path.name})
    hashes = _get_hash_dict(collection)
    hashes.pop(_get_file_hash_id(collection, document_path), None)
    _save_hashes(collection, hashes)


## Folder_path = path to e config files
def load_files_into_chroma(folder_path, client: chromadb.ClientAPI, collection_name):
    # Iterate over files in the folder

    collection_status, collection = ensure_collection(client, collection_name)


    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Only process text files (or adapt as needed for other file types)
        if os.path.isfile(file_path) and file_path.endswith('.txt'):
            # Open and read the content of each file
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            


            # Add the file content to the Chroma collection as a new chunk
            collection.add(
                documents=[file_content],
                metadatas=[{"filename": filename}],
                ids=[filename]
            )
            print(f"Added {filename} to Chroma database.")


def _parse_collection_files_groups_from_dir(base_dir: Path) -> dict[str: list[str]]:
    """
    parses the folder structure for two levels deep from the disk starting at `base_dir` into a python directory
   
    Expected/Example file_structure:
    ```
    base_dir(default: transpiled_files)/
    ├── Ansible (collection name 1)
    │   └── Ansible.md (file in collection named Ansible)
    ├── OpenShift (collection named OpenShift)
    │   ├── SingleNode/ (ignored)
    │   │    └── Test.md 
    │   └── Openshift.md (file in collection named Openshift)
    └── POWER10 (collection named POWER10)
        ├── S1012.anything_else (also ignored)
        └── E1050.md (file in collection named Power10)

    ``` 
    
    Will result in the following dict:
    
    ```
    {
        "Ansible": ["Ansible.md"],
        "OpenShift": ["Openshift.md"],
        "POWER10": ["E1050.md"],
    }
    ```
    

    :returns: The directory structure of folder to md files under folder
    """
    result = {}
    sub_dirs = map(
            lambda entry: entry.name,
            filter(
                lambda entry: entry.is_dir(), 
                os.scandir(base_dir)
            )
        )

    for directory in sub_dirs:
        files = list(
            map(
                lambda entry: entry.name,
                filter(
                    # filter for only markdown files:
                    lambda entry: entry.is_file() and os.path.splitext(entry)[-1] == ".md",
                    os.scandir(base_dir / directory) 
                )
            )
        )
        if files:
            result[directory.replace(' ', '_')] = files
    
    return result


def _calculate_file_hash(path: Path) -> str:
    """hashes the given file using sh256.

    :param path: The Path to the file to hash
    :returns: the hexdigits as string of the sha256 hash
    :raises IOError: If the given path does not point to a file.
    """
    
    if not path.is_file():
        raise IOError(f"cannot hash non-file object at {path}!")
    
    BUF_SIZE = 65536
    
    sha256 = hashlib.sha256()
    
    with open(path, 'rb', buffering=0) as f:
       while True:
        data = f.read(BUF_SIZE)
        if not data:
            break
        sha256.update(data) 
        
    return sha256.hexdigest()


def _get_file_hash_id(collection: Collection, file: Path) -> str:
    """get the dictionary key for a file id.

    :param collection: The collection in which the file resides
    :param file: Path to the file, used to extract the name. The File does not need to exist on disk.
    :returns: str - the file id for lookup in the hashes metadata dict.
    """
    return f"{collection.name}/{file.name}"

def _get_hash_dict(collection: Collection) -> dict[str, str]:
    """loads the hash directory from the metadata field of a collection if available

    :params collection: the collection to get the hashes from
    :returns: a dict of filename to hash (sha256), or an empty dict if no hashes were saved yet.
    """
    
    if collection.metadata:
        return json.loads(collection.metadata.get("hashes", "{}"))
    return {}


def _save_hashes(collection: Collection, hashes: dict[str, str]) -> None:
    """save a mapping (dict) of filenames to hashes into the metadatafield 
    `hashes` of the given collection.

    All unrelated metadata will be keept.

    :param collection: the collection to add the metadatafiled hashes to
    :param hashes: dictonary of filename to filehash (sha256)
    """
    
    meta_dict = collection.metadata or {}
    # metadata values cannot be dicts/nested therefore encoded as json
    meta_dict["hashes"] = json.dumps(hashes)
    collection.modify(metadata=meta_dict)


def _update_file_hash(collection: Collection, file_path: Path, hash: str) -> None:
    """updates the hash of a file (new or existing) in the collection metadata

    :param collection: The collection which conttains the file
    :param file_path: path to the file
    :param hash: The hash of the file
    """
    # Note: The hash is given as input, since it will already be calculated for change-detection
    #       before the need for an insert/update was determined.
    current_hashes = _get_hash_dict(collection)
    current_hashes[_get_file_hash_id(collection, file_path)] = hash
    _save_hashes(collection, current_hashes)


def load_files_from_md_directory_tree(chroma_client: ClientAPI, base_dir: Path, create_all_collection: bool = False) -> None:
    """Loads all markdown files which follow the expected file-tree structure into their 
    designated collection in the chroma db.
    
    Expected/Example file_structure:
    ```
    base_dir(default: transpiled_files)/
    ├── Ansible (collection name 1)
    │   └── Ansible.md (file in collection named Ansible)
    ├── OpenShift (collection named OpenShift)
    │   └── Openshift.md (file in collection named Openshift)
    └── POWER10 (collection named POWER10)
        ├── E1050.md (file in collection named Power10)
        ├── E1080.md
        ├── S1012.md
        └── ScaleOut.md
    ```

    :param chroma_client: The client connection to ChromaDB
    :param base_dir: The starting point (Path) of the directory structure
    :param create_all_collection: Boolean toggle whether an all collection containing all files should also be created.
    """

    file_groups = _parse_collection_files_groups_from_dir(base_dir)
    
    all_collection_status, all_collection = ensure_collection(chroma_client, ALL_COLLECTION_NAME) if create_all_collection else (None, None)
    if all_collection_status == CollectionStatus.COLLECTION_CREATION_FAILED:
        raise RuntimeError("clould not create All Topics collection!")
    
    all_hashes = _get_hash_dict(all_collection)
 
    statistics = {
        "colls_created": 0,
        "colls_modified": 0,
        "colls_deleted": 0,
        "files_modified": 0,
        "files_inserted": 0,
        "files_deleted": 0,
        "files_not_found": 0,
    }

    for collection_name, files in file_groups.items():
                
        collection_status, collection = ensure_collection(chroma_client, collection_name)
        if collection_status == CollectionStatus.COLLECTION_EXISTS:
            print(f"collection '{ collection_name }' already exists. Looking for changes")
            statistics["colls_modified"] += 1
        else:
            statistics["colls_created"] += 1
        
        print(f"Inserting Files into new collection '{ collection_name }'.")
        
        new_hashes = {} # change detection via sha256 hashes of the md files.
        current_hashes = _get_hash_dict(collection)
        
        for file_name in files:
            file_path: Path = base_dir / collection_name / file_name

            if not file_path.exists():
                print(f"File '{file_name}' was detected, but path '{file_path}' does not exists! Skipping File!", file = sys.stderr)
                statistics["files_not_found"] += 1
                continue
            
            file_local_id = _get_file_hash_id(collection, file_path)
            new_hashes[file_local_id] = _calculate_file_hash(file_path)
            
            if current_hashes.get(file_local_id) == None:
                print(f"Detected new file {file_name} in collection {collection_name}. Adding.")
                insert_document(file_path, collection)
                statistics["files_inserted"] += 1
                
                # TODO: manage if only the all collection need insertion.
                if create_all_collection:
                    insert_document(file_path, all_collection) 
                
            elif current_hashes.get(file_local_id) != new_hashes[file_local_id]:
                print(f"file { file_name } in { collection_name } was modified. Updating!")
                delete_document(file_path, collection)
                insert_document(file_path, collection)
                statistics["files_modified"] += 1

                if create_all_collection:
                    delete_document(file_path, all_collection)
                    insert_document(file_path, all_collection)

        
        deleted_files = set(current_hashes.keys()) - set(new_hashes.keys()) # files only currently in DB but not FS
        for file_id in deleted_files:
            print(f"File {file_id} is no longer present. Deleting from DB.")
            delete_document(Path(file_id), collection)
            statistics["files_deleted"] += 1
            
            if create_all_collection:
                delete_document(Path(file_id), all_collection)
            
        print(f"Completed updating collection '{ collection_name }'")
     
  
    db_collections = chroma_client.list_collections()
    current_collections = list(file_groups.keys())

    if create_all_collection:
        current_collections.append(ALL_COLLECTION_NAME)
    
    for collection in db_collections:
        if collection not in current_collections:
            # collection no longer a directory on disk. Removing.
            print(f"Detected deleted '{ collection }'. Removing from DB")
            chroma_client.delete_collection(collection) 
            
    # TODO: fancy output for statistics :)
    pprint(statistics)


def main() -> None:
    db_directory = Path(os.getenv("RAG_DB_DIR") or "./db")
    files_directory = Path(os.getenv("RAG_MD_FILE_DIR") or "transpiled_files/")

    if not db_directory.exists():
        db_directory.mkdir()

    if not files_directory.exists():
        print("DB files were not copied! Abort.", file=sys.stderr)
        sys.exit(1)

    chroma_client = chromadb.PersistentClient(path=str(db_directory))

    load_files_from_md_directory_tree(chroma_client, files_directory, True)
    print("Setup completed.")

    # Example query for testing
    collection = chroma_client.get_collection(name=ALL_COLLECTION_NAME, embedding_function=sentence_transformer_ef)
    result = collection.query(
        query_texts=["What is IBM POWER"],
        n_results=5,
        include=["documents"]
    )
    print(result)


if __name__ == "__main__":
    main()
