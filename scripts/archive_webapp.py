"""Simple archiving web app inspired by https://github.com/jamestonner89/sd-webui-civbrowser"""
import os
import json
from typing import List
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BASE_URL = "https://civitai.com/api/v1"
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "..", "archive_data")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

app = FastAPI(title="Civitai Archive", description="Archive model metadata and images for preservation")

class ArchiveResponse(BaseModel):
    model_id: int
    metadata_path: str
    image_paths: List[str]

@app.get("/archive/{model_id}", response_model=ArchiveResponse)
def archive_model(model_id: int):
    """Download metadata and preview images for a model and store them locally."""
    try:
        resp = requests.get(f"{BASE_URL}/models/{model_id}")
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
    data = resp.json()
    meta_path = os.path.join(ARCHIVE_DIR, f"{model_id}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    image_paths = []
    versions = data.get("modelVersions", [])
    if versions:
        images = versions[0].get("images", [])
        for idx, img in enumerate(images):
            url = img.get("url")
            if not url:
                continue
            try:
                r = requests.get(url)
                r.raise_for_status()
                ext = os.path.splitext(url)[1] or ".jpg"
                img_path = os.path.join(ARCHIVE_DIR, f"{model_id}_{idx}{ext}")
                with open(img_path, "wb") as out:
                    out.write(r.content)
                image_paths.append(img_path)
            except requests.RequestException:
                continue
    return ArchiveResponse(model_id=model_id, metadata_path=meta_path, image_paths=image_paths)

@app.get("/models")
def list_models():
    """List archived model metadata."""
    models = []
    for file in os.listdir(ARCHIVE_DIR):
        if file.endswith(".json"):
            with open(os.path.join(ARCHIVE_DIR, file), "r", encoding="utf-8") as f:
                models.append(json.load(f))
    return {"models": models}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
