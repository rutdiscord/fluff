import os
import zipfile

IGNORE_FILES = {"fluff_database.db", "fluff_database.db-wal", "fluff_database.db-shm"}

def make_backup(zip_name: str):
    """Makes a backup zip file containing all the data inside the root data folder, not including
    files that should be ignored.

    zip_name: name of the resulting zip file
    """
    with zipfile.ZipFile(f"{zip_name}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("data"):
            for file in files:
                if file not in IGNORE_FILES:
                    full_path = os.path.join(root, file)
                    zf.write(full_path)