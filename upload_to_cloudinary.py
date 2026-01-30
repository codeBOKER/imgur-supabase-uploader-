#!/usr/bin/env python3
import io
import sys
import os
from PIL import Image
from supabase import create_client, Client
from datetime import datetime, timezone

import cloudinary
import cloudinary.uploader

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- CONFIGURATION ---
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
SUPABASE_URL = "https://elwiqklpiusktqhgxplu.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SERVICE_ACCOUNT_FILE = 'service_account.json'

# Initialize Clients
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Google Drive API Setup
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

def get_now():
    return datetime.now(timezone.utc).isoformat()

def optimize_image_locally(raw_bytes, max_width=1600):
    """تحويل الصورة ومعالجتها في ذاكرة الـ GitHub Action Runner"""
    img = Image.open(io.BytesIO(raw_bytes))

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * float(ratio))
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    
    output = io.BytesIO()
    img.save(output, format="WEBP", quality=80, method=6)
    output.seek(0)
    return output

def download_file_from_drive(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()

def process_folder(folder_id, folder_name):
    print(f"\n📦 Starting Product: {folder_name}")
    
    try:
        
        product_data = {
            "header": folder_name,
            "description": folder_name,
            "price": 12.00,
            "is_active": True,
            "category_id": 4,
            "created_at": get_now(),
            "updated_at": get_now()
        }
        res = supabase.table("core_product").insert(product_data).execute()
        product_id = res.data[0]['id']

        
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        for file in files:
            if not any(ext in file['name'].lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                continue
            
            print(f"   🖼️ Processing {file['name']}...")
            raw_bytes = download_file_from_drive(file['id'])
            
            optimized_file = optimize_image_locally(raw_bytes)
            
            upload_result = cloudinary.uploader.upload(
                optimized_file,
                folder=f"my_store/{folder_name}",
                resource_type="image"
            )
            
            final_url = upload_result['secure_url']

            
            supabase.table("core_productcolor").insert({
                "name": "default",
                "image": final_url,
                "product_id": product_id,
                "is_available": True
            }).execute()
            print(f"      ✅ Done: {final_url}")

    except Exception as e:
        print(f"   ❌ Error in {folder_name}: {e}")

def main(parent_folder_id):
    query = f"'{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])

    if not folders:
        process_folder(parent_folder_id, "Main Folder")
    else:
        for folder in folders:
            process_folder(folder['id'], folder['name'])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <google_folder_id>")
    else:
        main(sys.argv[1])