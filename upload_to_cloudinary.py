#!/usr/bin/env python3
import io
import sys
import os
import requests
from pathlib import Path
from supabase import create_client, Client
from datetime import datetime, timezone

# Cloudinary Library
import cloudinary
import cloudinary.uploader

# Google API Libraries
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- CONFIGURATION ---
SUPABASE_URL = "https://elwiqklpiusktqhgxplu.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cloudinary Config (Get these from your Cloudinary Dashboard)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

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

def download_file_from_drive(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue()

def process_folder(folder_id, folder_name):
    print(f"\n📦 Processing Product: {folder_name}")
    
    product_data = {
        "header": folder_name,
        "description": folder_name,
        "price": 12.00,
        "is_active": True,
        "category_id": 4,
        "created_at": get_now(),
        "updated_at": get_now()
    }
    
    try:
        res = supabase.table("core_product").insert(product_data).execute()
        product_id = res.data[0]['id']
        print(f"   ✅ Created Product (ID: {product_id})")

        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])

        for file in files:
            if not any(ext in file['name'].lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                continue
            
            print(f"   🖼️  Processing: {file['name']}")
            raw_bytes = download_file_from_drive(file['id'])
            
            # --- Cloudinary Upload & Transformation ---
            
            upload_result = cloudinary.uploader.upload(
                raw_bytes,
                folder=f"products/{folder_name}",
                
                transformation=[
                    {'width': 1200, 'crop': "limit"}, 
                    {'quality': "auto"},            
                    {'fetch_format': "webp"}        
                ]
            )
            
            
            final_url = upload_result['secure_url']

            # 3. Link to Supabase
            color_data = {
                "name": "white",
                "color_code": "#FCFCFC",
                "image": final_url,
                "is_available": True,
                "product_id": product_id
            }
            supabase.table("core_productcolor").insert(color_data).execute()
            print(f"      🚀 Optimized & Hosted: {final_url}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

def main(parent_folder_id):
    query = f"'{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])

    if not folders:
        file_check = drive_service.files().get(fileId=parent_folder_id, fields="name").execute()
        process_folder(parent_folder_id, file_check['name'])
    else:
        for folder in folders:
            process_folder(folder['id'], folder['name'])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <google_folder_id>")
    else:
        main(sys.argv[1])