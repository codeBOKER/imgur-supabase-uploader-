#!/usr/bin/env python3
import io
import sys
import os
import requests
import tinify
from pathlib import Path
from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv

# Google API Libraries
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# --- CONFIGURATION ---
# Load environment variables from .env (if present)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-url.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-service-role-key")
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "0c4e136418d4fd9")
TINY_API_KEY = os.getenv("TINY_API_KEY", "1nwW4R5pCYDXgwTkStBkthqcWCKV66Ht")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")  # The JSON file from Google Cloud

# Initialize Clients
tinify.key = TINY_API_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Google Drive API Setup
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

def get_now():
    return datetime.now(timezone.utc).isoformat()

def format_size(bytes_num):
    for unit in ['B', 'KB', 'MB']:
        if bytes_num < 1024.0: return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} GB"

def download_file_from_drive(file_id):
    """Downloads file content into memory buffer."""
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue()

def process_folder(folder_id, folder_name):
    print(f"\n📦 Processing Product: {folder_name}")
    
    # 1. Insert Product into Supabase
    product_data = {
        "header": folder_name,
        "description": folder_name,
        "price": 12.00,
        "is_active": True,
        "category_id": 4,
        "created_at": get_now()
    }
    
    try:
        res = supabase.table("core_product").insert(product_data).execute()
        product_id = res.data[0]['id']
        print(f"   ✅ Created Product (ID: {product_id})")

        # 2. List all images in this folder
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])

        for file in files:
            if not any(ext in file['name'].lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                continue
            
            print(f"   🖼️  File: {file['name']}")
            
            # Cloud-to-Cloud Stream
            raw_bytes = download_file_from_drive(file['id'])
            
            # TinyPNG Compression
            print(f"      ☁️  Compressing {format_size(len(raw_bytes))}...")
            compressed_bytes = tinify.from_buffer(raw_bytes).to_buffer()
            print(f"      ✅ New Size: {format_size(len(compressed_bytes))}")

            # Imgur Upload
            headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
            img_res = requests.post("https://api.imgur.com/3/image", 
                                    headers=headers, 
                                    files={'image': compressed_bytes})
            imgur_url = img_res.json()['data']['link']

            # 3. Link to Supabase
            color_data = {
                "name": "white",
                "color_code": "#FCFCFC",
                "image": imgur_url,
                "is_available": True,
                "product_id": product_id
            }
            supabase.table("core_productcolor").insert(color_data).execute()
            print(f"      🔗 Linked: {imgur_url}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

def main(parent_folder_id):
    # Get list of subfolders (Products)
    query = f"'{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])

    if not folders:
        # If no subfolders, check if the ID itself is a product folder containing images
        file_check = drive_service.files().get(fileId=parent_folder_id, fields="name").execute()
        process_folder(parent_folder_id, file_check['name'])
    else:
        for folder in folders:
            process_folder(folder['id'], folder['name'])

if __name__ == "__main__":
    # Usage: python3 script.py YOUR_GOOGLE_FOLDER_ID
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <google_folder_id>")
    else:
        # You get this ID from the URL of your Google Drive folder
        main(sys.argv[1])