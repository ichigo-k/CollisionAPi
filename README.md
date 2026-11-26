# Collision API

A small FastAPI service that handles photo evidence for road-collision incident reports. Upload a set of photos for an incident and it will:

1. store the first photo at full resolution,
2. resize every photo to 1280×720 JPEG,
3. stitch the resized photos into an animated GIF that plays through the scene,
4. upload everything to **Supabase Storage** and record the links against the incident in a Supabase `media` table.

## Endpoints

### `POST /upload-images`

Multipart form upload.

| Field | Type | Notes |
| --- | --- | --- |
| `images` | file[] | One or more images. The first becomes the thumbnail. |
| `incident_id` | int | Optional. The incident these photos belong to. |

```bash
curl -X POST http://localhost:8000/upload-images \
  -F "images=@front.jpg" -F "images=@side.jpg" -F "images=@rear.jpg" \
  -F "incident_id=42"
```

Response:

```json
{
  "message": "Upload successful",
  "id": 7,
  "incident_id": 42,
  "path": "{\"thumbnail\": \"https://…/resized/…jpg\", \"gif\": \"https://…/gifs/…gif\"}"
}
```

### `GET /media/{file_path}`

Returns the public URL for a stored file.

## Storage layout

```
media/
  original/   first photo, unchanged
  resized/    1280×720 JPEG thumbnail
  gifs/       animated GIF of all photos
```

## Running locally

You need Python 3.11+ and a Supabase project with a public storage bucket (default name `media`) and a `media` table with columns `created_at`, `incident_id` and `path`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # add your Supabase URL and key
uvicorn main:app --reload
```

Interactive docs are at http://localhost:8000/docs.

## Tech stack

Python · FastAPI · Pillow · Supabase (Storage + Postgres)
