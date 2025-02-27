#!/usr/bin/env python3

"""
This file - when executed alone - runs the full demo pipeline:
1. convert pdf files at env(RAG_PDF_FILE_DIR) into markdown files (using docling)
2. Launch and insert chromadb with these files
3. run the gradio Webserver with the UI to perform RAG using chromadb and llamacpp

Requirements:
- The modelfile needs to be downloaded (gguf format)
- All environvariables from example.env must be set in the executing shell
    -> Or their defaults will be used. (NOTE: RAG_MODEL_PATH has no default!)
- all required python packages (see ansible/rag-environment and ansible/requirements.txt)
  must be installed.
"""

import os
from pathlib import Path
from typing import NoReturn


def step_fill_chroma_db() -> bool:
    from chromaDB_md import get_chroma_client, setup_chromadb_with_files

    print("Inserting md files into ChromaDB")
    client = get_chroma_client()
    setup_chromadb_with_files(client)
    return True


def step_convert_pdfs() -> bool:
    from converter_docling import convert_dir_files

    print("converting pdf files to md")
    convert_dir_files(
        Path(os.getenv("RAG_PDF_FILE_DIR")),
        Path(os.getenv("RAG_MD_FILE_DIR")),
    )
    return True


def step_run_server() -> NoReturn:
    from run_model import run_gradio_server

    print("starting gradio server")
    run_gradio_server()


def run_pipeline() -> NoReturn:
    step_convert_pdfs()
    step_fill_chroma_db()
    step_run_server()


if __name__ == "__main__":
    run_pipeline()
