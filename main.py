from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from supabase import create_client, Client
from PIL import Image
import io
import json
import time


SUPABASE_URL = "your url "
SUPABASE_KEY = "key"
BUCKET_NAME = "media"


# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-images")
async def upload_images(images: List[UploadFile] = File(...), incident_id: int = Form(None)):
    if not images:
        raise HTTPException(status_code=400, detail="No images uploaded.")

    resized_images = []
    filenames = []

    first_img = images[0]
    filename = f"{int(time.time())}-{first_img.filename}"
    file_content = await first_img.read()

    try:
        # Upload original image
        original_path = f"original/{filename}"
        original_response = supabase.storage.from_(BUCKET_NAME).upload(
            original_path, file_content, {"Content-Type": first_img.content_type}
        )
        if not original_response:
            raise Exception("Failed to upload original image to Supabase.")

        original_url = supabase.storage.from_(BUCKET_NAME).get_public_url(original_path)

        # Resize and upload thumbnail
        img = Image.open(io.BytesIO(file_content)).convert("RGB")
        resized = img.resize((1280, 720), Image.LANCZOS)
        buffered = io.BytesIO()
        resized.save(buffered, format="JPEG")
        resized_content = buffered.getvalue()

        resized_path = f"resized/{filename}"
        resized_response = supabase.storage.from_(BUCKET_NAME).upload(
            resized_path, resized_content, {"Content-Type": "image/jpeg"}
        )
        if not resized_response:
            raise Exception("Failed to upload resized image to Supabase.")

        resized_url = supabase.storage.from_(BUCKET_NAME).get_public_url(resized_path)
        resized_images.append(resized_url)
        filenames.append(filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process first image: {str(e)}")

    # Process remaining images
    other_images = images[1:]
    other_contents = [await img.read() for img in other_images]
    other_resized_contents = []
    for content in other_contents:
        img = Image.open(io.BytesIO(content)).convert("RGB")
        resized = img.resize((1280, 720), Image.LANCZOS)
        buffered = io.BytesIO()
        resized.save(buffered, format="JPEG")
        other_resized_contents.append(buffered.getvalue())

    # Create GIF
    gif_filename = f"{int(time.time())}-output.gif"
    gif_path = f"gifs/{gif_filename}"
    try:
        images_for_gif = [Image.open(io.BytesIO(content)) for content in [resized_content] + other_resized_contents]
        buffered = io.BytesIO()
        images_for_gif[0].save(
            buffered,
            format="GIF",
            save_all=True,
            append_images=images_for_gif[1:],
            duration=100,
            loop=0
        )
        gif_content = buffered.getvalue()
        gif_response = supabase.storage.from_(BUCKET_NAME).upload(
            gif_path, gif_content, {"Content-Type": "image/gif"}
        )
        if not gif_response:
            raise Exception("Failed to upload GIF to Supabase.")

        gif_url = supabase.storage.from_(BUCKET_NAME).get_public_url(gif_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create GIF: {str(e)}")

    # Store metadata in Supabase DB
    try:
        data = {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "incident_id": int(incident_id) if incident_id else 1,
            "path": json.dumps({"thumbnail": resized_url, "gif": gif_url})
        }
        response = supabase.table("media").insert(data).execute()
        record = response.data[0] if response.data and isinstance(response.data, list) else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save metadata: {str(e)}")

    return JSONResponse({"message": "Upload successful", **record})

@app.get("/media/{file_path:path}")
async def get_media(file_path: str):
    base_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/"
    full_url = base_url + file_path
    return JSONResponse({"url": full_url})
