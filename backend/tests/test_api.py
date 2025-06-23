import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import config
import logging

client = TestClient(app)
logging.basicConfig(level=logging.INFO)

# Define API prefix that matches the app configuration in main.py
API_PREFIX = "/api"


def setup_module(module):
    module.upload_dir = tempfile.mkdtemp()
    module.transcript_dir = tempfile.mkdtemp()
    config.UPLOAD_DIR = module.upload_dir
    config.TRANSCRIPT_DIR = module.transcript_dir
    logging.info(f"[setup] Using temp upload_dir={module.upload_dir}, transcript_dir={module.transcript_dir}")

def teardown_module(module):
    shutil.rmtree(module.upload_dir)
    shutil.rmtree(module.transcript_dir)
    logging.info("[teardown] Temp dirs cleaned up.")

def test_upload_and_caption_and_transcript():
    logging.info("Running test_upload_and_caption_and_transcript...")
    filename = "test.mp4"
    file_content = b"dummy video content"
    
    # Use the correct API path with prefix
    response = client.post(f"{API_PREFIX}/upload", files={"file": (filename, file_content, "video/mp4")})
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
    assert response.json()["status"] == "uploaded"
    logging.info("Upload successful.")

    response = client.post(f"{API_PREFIX}/generate_captions", params={"filename": filename})
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
    assert response.json()["status"] == "processing"
    transcript_file = response.json()["transcript_file"]
    logging.info("Caption generation triggered.")

    from app.services.caption import generate_transcript
    generate_transcript(filename)

    response = client.get(f"{API_PREFIX}/transcript/{transcript_file}")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert "segments" in data
    assert len(data["segments"]) > 0
    logging.info("Transcript fetch and content verified.")

def test_upload_missing_file():
    logging.info("Running test_upload_missing_file...")
    response = client.post(f"{API_PREFIX}/generate_captions", params={"filename": "doesnotexist.mp4"})
    assert response.status_code == 404, f"Expected 404 but got {response.status_code}. Response: {response.text}"
    
    # The response format may differ based on FastAPI's error handling
    response_data = response.json()
    if "detail" in response_data:
        assert response_data["detail"] == "Video not found."
    else:
        assert "error" in response_data
    
    logging.info("Missing file error correctly handled.")

def test_transcript_missing():
    logging.info("Running test_transcript_missing...")
    response = client.get(f"{API_PREFIX}/transcript/doesnotexist.mp4.json")
    assert response.status_code == 404, f"Expected 404 but got {response.status_code}. Response: {response.text}"
    
    # The response format may differ based on FastAPI's error handling
    response_data = response.json()
    if "detail" in response_data:
        assert response_data["detail"] == "Transcript not found."
    else:
        assert "error" in response_data
    
    logging.info("Missing transcript error correctly handled.")
