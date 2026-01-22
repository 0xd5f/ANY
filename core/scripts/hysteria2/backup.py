import zipfile
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

DB_NAME = "blitz_panel"
BACKUP_ROOT_DIR = Path("/opt/hysbackup")
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
BACKUP_FILENAME = BACKUP_ROOT_DIR / f"hysteria_backup_{TIMESTAMP}.zip"
TEMP_DUMP_DIR = BACKUP_ROOT_DIR / f"mongodump_{TIMESTAMP}"

FILES_TO_BACKUP = [
    Path("/etc/hysteria/ca.key"),
    Path("/etc/hysteria/ca.crt"),
    Path("/etc/hysteria/config.json"),
    Path("/etc/hysteria/.configs.env"),
]

def create_backup():
    try:
        BACKUP_ROOT_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_DUMP_DIR.mkdir(parents=True)

        print(f"Dumping database '{DB_NAME}'...")
        mongodump_cmd = [
            "mongodump",
            f"--db={DB_NAME}",
            f"--out={TEMP_DUMP_DIR}"
        ]
        subprocess.run(mongodump_cmd, check=True, capture_output=True)
        print("Database dump successful.")

        print(f"Creating backup archive: {BACKUP_FILENAME}")
        with zipfile.ZipFile(BACKUP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in FILES_TO_BACKUP:
                if file_path.exists() and file_path.is_file():
                    zipf.write(file_path, arcname=file_path.name)
                    print(f"  - Added {file_path.name}")
                else:
                    print(f"  - Warning: Skipping missing file {file_path}")

            dump_content_path = TEMP_DUMP_DIR / DB_NAME
            if dump_content_path.exists():
                for file_path in dump_content_path.rglob('*'):
                    arcname = file_path.relative_to(TEMP_DUMP_DIR)
                    zipf.write(file_path, arcname=arcname)
                print(f"  - Added database dump for '{DB_NAME}'")

        print("\nBackup successfully created.")

    except FileNotFoundError:
        print("\nBackup failed! 'mongodump' command not found. Is MongoDB installed and in your PATH?")
    except subprocess.CalledProcessError as e:
        print("\nBackup failed! Error during mongodump.")
        print(f"  - Stderr: {e.stderr.decode().strip()}")
    except Exception as e:
        print(f"\nBackup failed! An unexpected error occurred: {e}")
    finally:
        if TEMP_DUMP_DIR.exists():
            shutil.rmtree(TEMP_DUMP_DIR)
            print("Temporary dump directory cleaned up.")

if __name__ == "__main__":
    create_backup()