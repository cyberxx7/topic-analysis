"""
delivery/upload_drive.py — Google Drive Uploader (Service Account)

Uses a Google Service Account for authentication — no tokens that expire,
no browser login required. Works reliably in GitHub Actions every time.

── One-time setup ────────────────────────────────────────────────────────────
1. Go to https://console.cloud.google.com
2. Enable the Google Drive API
3. IAM & Admin → Service Accounts → Create Service Account
4. Keys tab → Add Key → Create new key → JSON → download the file
5. Share your Google Drive folder with the service account email
   (e.g. name@project.iam.gserviceaccount.com) as Editor
6. Add to .env:
      GOOGLE_DRIVE_FOLDER_ID=<your_folder_id>
      GOOGLE_SERVICE_ACCOUNT_KEY=<full contents of the JSON key file>

── GitHub Actions setup ──────────────────────────────────────────────────────
Add two secrets to your GitHub repo
(Settings → Secrets and variables → Actions → New repository secret):

  GOOGLE_DRIVE_FOLDER_ID      ← your Drive folder ID
  GOOGLE_SERVICE_ACCOUNT_KEY  ← full contents of the service account JSON key
──────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
except ImportError:
    build = MediaFileUpload = service_account = None

load_dotenv()

FOLDER_ID  = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
SA_KEY_ENV = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "")  # full JSON as env var
SA_KEY_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")  # or file path

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Filenames (relative to the run's output_dir) and their MIME types
UPLOAD_FILENAMES = [
    ("articles.csv",          "text/csv"),
    ("thegrio_com.csv",       "text/csv"),
    ("theroot_com.csv",       "text/csv"),
    ("newsone_com.csv",       "text/csv"),
    ("capitalbnews_org.csv",  "text/csv"),
    ("ebony_com.csv",         "text/csv"),
    ("essence_com.csv",       "text/csv"),
    ("blavity_com.csv",       "text/csv"),
    ("editorial_report.html", "text/html"),
    ("editorial_report.pdf",  "application/pdf"),
]


def _load_credentials():
    """
    Load service account credentials from environment variable or file.
    Prefers GOOGLE_SERVICE_ACCOUNT_KEY env var (used in GitHub Actions),
    falls back to a local service_account.json file.
    """
    if service_account is None:
        _abort("Google API libraries not installed.\n"
               "  Run: pip install google-api-python-client google-auth")
        return None

    # Try env var first (GitHub Actions)
    if SA_KEY_ENV:
        try:
            key_data = json.loads(SA_KEY_ENV)
            return service_account.Credentials.from_service_account_info(
                key_data, scopes=SCOPES
            )
        except Exception as e:
            _abort(f"Failed to load service account from env var: {e}")
            return None

    # Fall back to local file
    if os.path.exists(SA_KEY_FILE):
        try:
            return service_account.Credentials.from_service_account_file(
                SA_KEY_FILE, scopes=SCOPES
            )
        except Exception as e:
            _abort(f"Failed to load service account from {SA_KEY_FILE}: {e}")
            return None

    _abort(
        "No service account credentials found.\n"
        "  Set GOOGLE_SERVICE_ACCOUNT_KEY env var, or place service_account.json\n"
        "  in the project root."
    )
    return None


def run_upload(output_dir: str = "outputs", run_date: str = None) -> None:
    """
    Upload all files from output_dir to a dated subfolder in Google Drive.

    Args:
        output_dir: local path to the run's output directory (e.g. outputs/2026-03-27)
        run_date:   label for the Drive subfolder (defaults to today's YYYY-MM-DD)
    """
    from datetime import datetime as _dt
    if run_date is None:
        run_date = _dt.now().strftime("%Y-%m-%d")

    print(f"\n[drive] ── Starting Drive Upload ({run_date}) ──")

    # ── Pre-flight checks ─────────────────────────────────────────────
    if not FOLDER_ID:
        _abort(
            "GOOGLE_DRIVE_FOLDER_ID is not set.\n"
            "  Add it to your .env file:  GOOGLE_DRIVE_FOLDER_ID=<folder_id>\n"
            "  Copy the ID from your Drive folder URL."
        )
        return

    # ── Load service account credentials ─────────────────────────────
    creds = _load_credentials()
    if creds is None:
        return

    service = build("drive", "v3", credentials=creds)

    # ── Verify root folder is accessible ─────────────────────────────
    try:
        folder = service.files().get(fileId=FOLDER_ID, fields="id,name").execute()
        print(f"[drive] ✓ Connected to folder: {folder.get('name', FOLDER_ID)}")
    except Exception:
        _abort(
            f"Cannot access Drive folder: {FOLDER_ID}\n"
            "  Make sure the folder is shared with the service account email as Editor."
        )
        return

    # ── Get or create the dated subfolder ────────────────────────────
    subfolder_id = _get_or_create_subfolder(service, FOLDER_ID, run_date)
    print(f"[drive] ✓ Uploading into subfolder: {run_date}")

    # ── Upload each file ──────────────────────────────────────────────
    uploaded, skipped = 0, 0
    for filename, mime_type in UPLOAD_FILENAMES:
        file_path = os.path.join(output_dir, filename)
        if not os.path.exists(file_path):
            print(f"[drive]   ⚠ Skipped (not found): {file_path}")
            skipped += 1
            continue
        _upload_or_update(service, file_path, mime_type, subfolder_id)
        uploaded += 1

    print(f"\n[drive] ✓ Uploaded {uploaded} file(s), skipped {skipped}")
    print("[drive] ── Upload Complete ──\n")


def _get_or_create_subfolder(service, parent_id: str, name: str) -> str:
    """Return the ID of a subfolder named `name` inside `parent_id`, creating it if needed."""
    q = (
        f"name='{name}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    results = service.files().list(q=q, fields="files(id,name)").execute()
    existing = results.get("files", [])
    if existing:
        return existing[0]["id"]
    folder_meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=folder_meta, fields="id").execute()
    return folder["id"]


def _upload_or_update(
    service, local_path: str, mime_type: str, folder_id: str
) -> None:
    """Upload a file, overwriting if it already exists in the folder."""
    filename = os.path.basename(local_path)

    results = service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
        fields="files(id,name)",
    ).execute()
    existing = results.get("files", [])

    size_kb = round(os.path.getsize(local_path) / 1024, 1)
    media   = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)

    if existing:
        service.files().update(
            fileId=existing[0]["id"],
            media_body=media,
        ).execute()
        print(f"[drive]   ↻ Updated:  {filename}  ({size_kb} KB)")
    else:
        service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        print(f"[drive]   ↑ Uploaded: {filename}  ({size_kb} KB)")


def _abort(message: str) -> None:
    print(f"\n[drive] ✗ {message}\n[drive] Skipping upload.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Drive uploader")
    parser.add_argument("--output-dir", default="outputs", help="Output directory to upload")
    parser.add_argument("--run-date",   default=None,      help="Subfolder name in Drive (YYYY-MM-DD)")
    args = parser.parse_args()
    run_upload(output_dir=args.output_dir, run_date=args.run_date)
