import os
import shutil

# Define paths
base_folder = r"D:\PACKAGES\DJ_WAANVERSE_AUTH"
folders_to_delete = [
    os.path.join(base_folder, "dist"),
    os.path.join(base_folder, "build"),
    os.path.join(base_folder, "dj_waanverse_auth.egg-info"),
]

# Delete specified folders if they exist
for folder in folders_to_delete:
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"Deleted: {folder}")
