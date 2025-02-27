# RAG Pipeline for RedBooks

This repository provides a Retrieval-Augmented Generation (RAG) pipeline for processing and utilizing RedBooks. The RedBooks are pre-converted into markdown files using the Python library `docling`. This pipeline uses ChromaDB for vector database storage and `llama-cpp-python` for Large Language Model (LLM) inference.

## Prerequisites

Before using this project, ensure you have the following dependencies installed:

- **[ChromaDB](https://github.com/chroma-core/chroma):** A vector database for storing embeddings.
- **[llama-cpp-python](https://github.com/abetlen/llama-cpp-python):** Python bindings for running LLaMA-based models locally.

For ppc64le you can use these commands to get chroma, llama.cpp.python and other libraries:
```sh
micromamba create -n env python=3.10
micromamba install -c rocketce -c defaults pytorch-cpu scikit-learn pyyaml httptools onnxruntime "pandas<1.6.0" tokenizers
pip install -U --extra-index-url https://repo.fury.io/mgiessing --prefer-binary chromadb transformers psutil langchain sentence_transformers gradio==3.50.2 llama-cpp-python
```

or use the [rag-environment.yml](ansible/rag-environment.yml) (conda environment) and [requirements.pip](ansible/requirements.txt) (pip requirements not found in conda) respectively:
```sh
micromamba create -f ansible/rag-environment.yml
micromamba run -n rag-demo pip install -U --extra-index-url https://repo.fury.io/mgiessing --prefer-binary -r ansible/requirements.txt
```


## Manual Installation

Install the other libraries with pip for x86 and with conda (rocketce or defaults as the channel)

## Usage

To generate the vector database from your PDF and/or markdown files:

1. Your pdf/markdown files should be located in a folder with a subfolder for each collection (will result in a drop-down entry to select from for context usage when using gradio.):
```txt
 base_dir(e.g.: db_files_md)/
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
(the same goes for pdf files just with the .pdf extension)

2. Configuring the environment. 
   To tell all following scripts about the desired configuration the following environment variables can be set (see [example.env](example.env)):
   ```sh
   RAG_DB_DIR=db/ # folder for internal db file storage
   RAG_MD_FILE_DIR=db_files_md/ # folder containing markdown files (will also be filled when running the converting step)
   RAG_PDF_FILE_DIR=db_files_pdf/ # folder containing all pdf files
   RAG_MODEL_PATH=DeepSeek-R1-Distill-Qwen-14B-Q8_0.gguf # the model path to use
   RAG_PORT=7680 # server port
   ```

3. Convert PDF files to markdown (OPTIONAL)
   To convert all PDF files in `RAG_PDF_FILE_DIR` to markdown files saved into the `RAG_MD_FILE_DIR` simply run the [`converter_docling.py`](converter_docling.py) script from the conda environment:
   ```sh
   # set -a && source example.env && set +a # add env variables
   micromamba run -n rag-demo python converter_docling.py
   ```

4. Run the [`chromaDB_md.py`](chromaDB_md.py) script to fill the vector database with the files in `RAG_MD_FILE_DIR`:
   ```sh
   micromamba run -n rag-demo python chromaDB_md.py
   ```
   This will create a vector database in the `RAG_DB_DIR` directory. The database includes a collection for each subfolder of the `RAG_MD_FILE_DIR` as well as an `All_Topics` collection including all files combined.
5. Download the desired Model gguf file
   using the huggingface cli the desired model gguf file can be downloaded and the `RAG_MODEL_PATH` pointed at it:
   ```sh
   micromamba run -n rag-demo huggingface-cli download bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF --include "DeepSeek-R1-Distill-Qwen-14B-Q8_0.gguf" --local-dir ./
   export RAG_MODEL_PATH="$(PWD)/DeepSeek-R1-Distill-Qwen-14B-Q8_0.gguf"
   ```

6. Run The server
   Finally the [`run_model.py`](run_model.py) script can be used to start the server:
   ```sh
   micromamba run -n rag-demo python run_model.py
   ```
   To continuously run this server on a LPAR we recommend the installation via a systemd service. A Template for such a service can be found under the [systemd folder](systemd/rag-demo.service).

### Configure the LLM

To use the Large Language Model with the context from the vector DB (LLM), download the desired modell in gguf format and set the `RAG_MODEL_PATH` environment variable to its location.

## Alternative Installation: Ansible Playbooks

Alternatively this demo can be installed on a remote or local ppc64le RHEL host using the ansible playbook in the `ansible` directory.

For possible configuration options see the [example inventory file](ansible/example-inventory.yml).

## Folder Structure

- `/db`: Contains the vector database with collections generated by ChromaDB.
- `chromaDB_md.py`: Script for creating the vector database.
- `run_model.py`: Script for running the RAG pipeline using the configured LLM.

## Notes

- Ensure the RedBooks markdown files are in the expected format before running the pipeline.
- Make sure the GGUF model is compatible with `llama-cpp-python`.

## Contributing

If you would like to contribute to this project, feel free to fork the repository, make changes, and submit a pull request. 

## License

This project is licensed under the [MIT License](LICENSE). Feel free to use, modify, and distribute this project.

---

Happy experimenting with the RAG Pipeline for RedBooks!

