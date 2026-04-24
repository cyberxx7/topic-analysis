"""
delivery/upload_drive.py — Google Drive Uploader (OAuth 2.0)

Uses OAuth 2.0 with a published app so refresh tokens never expire.
Works silently in GitHub Actions with no browser interaction required.

── One-time setup ────────────────────────────────────────────────────────────
1. Go to https://console.cloud.google.com
2. Enable the Google Drive API
3. APIs & Services → Credentials → Create Credentials → OAuth client ID
   → Application type: Desktop app → download JSON → save as credentials.json
4. APIs & Services → OAuth consent screen → publishing status must be "In production"
   (this ensures the refresh token never expires)
5. Run the auth flow once locally:
      python delivery/upload_drive.py --auth
   A browser window opens → sign in → approve access → token.json is saved
6. Add to .env:
      GOOGLE_DRIVE_FOLDER_ID=<your_folder_id>

── GitHub Actions setup ──────────────────────────────────────────────────────
Add three secrets to your GitHub repo
(Settings → Secrets and variables → Actions → New repository secret):

  GOOGLE_DRIVE_FOLDER_ID   ← your Drive folder ID
  GOOGLE_OAUTH_CREDENTIALS ← full contents of credentials.json
  GOOGLE_OAUTH_TOKEN       ← full contents of token.json
──────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import argparse
from dotenv import load_dotenv

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except ImportError:
    build = MediaFileUpload = Credentials = Request = None

load_dotenv()

FOLDER_ID        = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
CREDENTIALS_PATH = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE", "credentials.json")
TOKEN_PATH       = os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.json")

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Filenames (relative to the run's output_dir) and their MIME types
UPLOAD_FILENAMES = [
    ("articles.csv",          "text/csv"),
    ("articles_tagged.csv",   "text/csv"),
    ("thegrio_com.csv",       "text/csv"),
    ("theroot_com.csv",       "text/csv"),
    ("newsone_com.csv",       "text/csv"),
    ("capitalbnews_org.csv",  "text/csv"),
    ("ebony_com.csv",         "text/csv"),
    ("essence_com.csv",       "text/csv"),
    ("blavity_com.csv",       "text/csv"),
    ("21ninety_com.csv",      "text/csv"),
    ("travelnoire_com.csv",   "text/csv"),
    ("afrotech_com.csv",      "text/csv"),
    ("editorial_report.html", "text/html"),
    ("editorial_report.pdf",  "application/pdf"),
]


def run_auth() -> None:
    """
    One-time OAuth browser flow. Run this locally once to generate token.json.
    The app must be published (not in testing) for the token to never expire.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing dependency. Run:  pip install google-auth-oauthlib")
        sys.exit(1)

    if not os.path.exists(CREDENTIALS_PATH):
        print(f"\n[drive] ✗ credentials.json not found at: {CREDENTIALS_PATH}")
        print("  Download it from Google Cloud Console:")
        print("  APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON")
        sys.exit(1)

    print("\n[drive] Opening browser for Google sign-in...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"\n[drive] ✓ Authenticated successfully!")
    print(f"[drive] ✓ Token saved → {TOKEN_PATH}")
    print()
    print("── GitHub Actions: update these repo secrets ─────────────────────")
    print("  GOOGLE_DRIVE_FOLDER_ID   ← your Drive folder ID")
    print(f"  GOOGLE_OAUTH_CREDENTIALS ← paste full contents of {CREDENTIALS_PATH}")
    print(f"  GOOGLE_OAUTH_TOKEN       ← paste full contents of {TOKEN_PATH}")
    print("──────────────────────────────────────────────────────────────────")


def run_upload(output_dir: str = "outputs", run_date: str = None) -> None:
    """
    Upload all files from output_dir to a dated subfolder in Google Drive.

    Args:
        output_dir: local path to the run's output directory (e.g. outputs/2026-04-24)
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
            "  Add it to your .env file:  GOOGLE_DRIVE_FOLDER_ID=<folder_id>"
        )
        return

    if not os.path.exists(TOKEN_PATH):
        _abort(
            f"No OAuth token found at {TOKEN_PATH}.\n"
            "  Run this once locally:  python delivery/upload_drive.py --auth"
        )
        return

    if build is None:
        _abort(
            "Google API libraries not installed.\n"
            "  Run: pip install google-api-python-client google-auth google-auth-oauthlib"
        )
        return

    # ── Load and refresh credentials ─────────────────────────────────
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
                print("[drive] ✓ Token refreshed")
            except Exception as exc:
                _abort(
                    f"Token refresh failed: {exc}\n"
                    "  Re-run locally:  python delivery/upload_drive.py --auth"
                )
                return
        else:
            _abort(
                "OAuth token is expired and has no refresh token.\n"
                "  Re-run locally:  python delivery/upload_drive.py --auth"
            )
            return

    service = build("drive", "v3", credentials=creds)

    # ── Verify root folder is accessible ─────────────────────────────
    try:
        folder = service.files().get(fileId=FOLDER_ID, fields="id,name").execute()
        print(f"[drive] ✓ Connected to folder: {folder.get('name', FOLDER_ID)}")
    except Exception:
        _abort(
            f"Cannot access Drive folder: {FOLDER_ID}\n"
            "  Check the folder ID and make sure it exists in your Drive."
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
    parser.add_argument(
        "--auth", action="store_true",
        help="Run one-time browser login to generate token.json"
    )
    args = parser.parse_args()

    if args.auth:
        run_auth()
    else:
        run_upload()
