import os
import shutil

# Define paths
base_folder = r"D:\PACKAGES\DJ_WAANVERSE_AUTH"
folders_to_delete = [
    os.path.join(base_folder, "tests"),
    os.path.join(base_folder, "dist"),
    os.path.join(base_folder, "build"),
    os.path.join(base_folder, "dj_waanverse_auth.egg-info"),
]

source_folder = r"D:\PACKAGES\DJ_WAANVERSE_AUTH\demo\tests"
destination_folder = os.path.join(base_folder, "tests")  # Ensure correct path

# Delete specified folders if they exist
for folder in folders_to_delete:
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"Deleted: {folder}")

# Copy the "tests" folder from source to destination
shutil.copytree(source_folder, destination_folder)
print("Folder copied successfully.")
