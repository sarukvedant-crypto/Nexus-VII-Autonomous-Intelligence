"""
J.A.R.V.I.S. Google Drive Downloader Module (Official API)
============================================================
Downloads files and folders from Google Drive shared links
using the official google-api-python-client to bypass pagination limits.
"""
import os
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from .calendar_module import get_google_credentials

def get_default_download_dir():
    """Returns the user's Downloads folder."""
    return os.path.join(os.path.expanduser("~"), "Downloads")

def _sanitize_name(name):
    """Removes invalid characters and trailing spaces for Windows paths."""
    # Remove invalid Windows characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Strip trailing whitespace and dots which Windows hates
    return name.strip('. ')

def _get_drive_service():
    creds = get_google_credentials()
    return build('drive', 'v3', credentials=creds)

import time

def _download_single_file(service, file_id, file_name, output_dir, max_retries=3):
    """Downloads a single file and returns the path. Retries on failure."""
    os.makedirs(output_dir, exist_ok=True)
    file_name = _sanitize_name(file_name)
    file_path = os.path.join(output_dir, file_name)
    
    # If file exists, add a suffix
    base, ext = os.path.splitext(file_name)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(output_dir, f"{base} ({counter}){ext}")
        counter += 1

    fh = None
    for attempt in range(max_retries):
        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024*5) # 5MB chunks
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.close()
            return file_path
        except Exception as e:
            if fh:
                try:
                    fh.close()
                except:
                    pass
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff
            else:
                raise Exception(f"Failed to download {file_name} after {max_retries} attempts: {e}")

def _download_folder_recursive(service, folder_id, current_output_dir):
    """Recursively downloads all contents of a Google Drive folder."""
    os.makedirs(current_output_dir, exist_ok=True)
    downloaded_count = 0
    page_token = None
    
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        items = results.get('files', [])
        
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # It's a subfolder, recurse!
                safe_subfolder_name = _sanitize_name(item['name'])
                subfolder_dir = os.path.join(current_output_dir, safe_subfolder_name)
                downloaded_count += _download_folder_recursive(service, item['id'], subfolder_dir)
            else:
                # It's a file, download it
                try:
                    _download_single_file(service, item['id'], item['name'], current_output_dir)
                    downloaded_count += 1
                except Exception as e:
                    print(f"Skipping {item['name']} due to error: {e}")
                
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break
            
    return downloaded_count

def download_drive_link(url, output_dir=None):
    """
    Downloads a file or folder from a Google Drive link.
    
    Args:
        url: A Google Drive sharing URL (file or folder).
        output_dir: Optional output directory. Defaults to user's Downloads folder.
    
    Returns:
        A status string describing what was downloaded and where.
    """
    if not output_dir:
        output_dir = get_default_download_dir()
    
    os.makedirs(output_dir, exist_ok=True)

    try:
        service = _get_drive_service()
        
        # Detect if it's a folder link
        is_folder = "/folders/" in url or "folder" in url.lower()

        if is_folder:
            # Extract folder ID from URL
            folder_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
            if not folder_match:
                return f"Could not extract folder ID from URL: {url}"
            
            folder_id = folder_match.group(1)
            
            # First, try to get the folder name to create a sub-directory
            try:
                folder_meta = service.files().get(fileId=folder_id, fields="name", supportsAllDrives=True).execute()
                folder_name = _sanitize_name(folder_meta.get("name", f"Drive_Folder_{folder_id}"))
            except Exception:
                folder_name = _sanitize_name(f"Drive_Folder_{folder_id}")
                
            folder_output_dir = os.path.join(output_dir, folder_name)
            
            # Recursively download all files and subfolders
            total_downloaded = _download_folder_recursive(service, folder_id, folder_output_dir)
            
            return f"Successfully downloaded {total_downloaded} file(s) from Google Drive folder '{folder_name}' to: {folder_output_dir}"

        else:
            # Single file download
            file_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
            if not file_match:
                # Some links look like ?id=...
                id_match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
                if id_match:
                    file_id = id_match.group(1)
                else:
                    return f"Could not extract file ID from URL: {url}"
            else:
                file_id = file_match.group(1)
                
            # Get file metadata to get the actual name
            file_meta = service.files().get(fileId=file_id, fields="name", supportsAllDrives=True).execute()
            file_name = file_meta.get("name", f"drive_file_{file_id}")
            
            _download_single_file(service, file_id, file_name, output_dir)
            return f"Successfully downloaded '{file_name}' to: {output_dir}"

    except Exception as e:
        return f"Google Drive API download failed: {e}"
