# Imgur / Supabase / Cloudinary uploader

Small utilities to upload images to Imgur or Cloudinary and link them to Supabase.

Quick start

- Requirements: Python 3.8+
- Install dependencies:

```bash
pip install -r requirements.txt
```

Configuration

- Create or obtain the following credentials and place them in the project root or export as env vars:
   - `IMGUR_CLIENT_ID` — Imgur application Client ID (anonymous upload)
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` — Cloudinary credentials (used by `upload_to_cloudinary.py`)
   - `SERVICE_ACCOUNT_FILE` — path to Google service account JSON (used by upload scripts)
   - `SUPABASE_URL` and `SUPABASE_KEY` — Supabase project URL and service role key (used by upload scripts)

Usage

- Upload images from a Google Drive folder to Imgur and link to Supabase:

```bash
python upload_to_imgur.py <google_folder_id>
```

- Upload images from a Google Drive folder to Cloudinary and link to Supabase:

```bash
python upload_to_cloudinary.py <google_folder_id>
```

- There is also `uploadToSupabase.py` (empty placeholder in this repo) for Supabase-specific operations.

Files

- `upload_to_imgur.py`: main script that downloads images from Google Drive, compresses with TinyPNG, uploads to Imgur, and inserts product records into Supabase.
- `upload_to_cloudinary.py`: script that downloads images from Google Drive, uploads to Cloudinary with automatic optimization, and inserts product records into Supabase.
- `uploadToSupabase.py`: additional helper (currently empty).
- `service_account.json`: Google service account credentials (should not be committed).

Security

- Do not commit credentials. `.gitignore` already excludes `*.json` and `*.xlsx`.

Problems or questions

- Open an issue or ask for help; I can help pin dependency versions or add a CLI parser.
