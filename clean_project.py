import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def clean_migrations():
    for root, dirs, files in os.walk(BASE_DIR):
        # Skip env directory
        if "env" in root.split(os.sep):
            continue
        if os.path.basename(root) == "migrations":
            for file in files:
                if file != "__init__.py":
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")


if __name__ == "__main__":
    clean_migrations()
