from pathlib import Path
import os


def create_project_structure():
    # Define the project root directory
    root_dir = Path(__file__).parent

    # Define all required directories
    directories = [
        "src",
        "src/core",
        "src/ui",
        "src/utils",
        "data",
        "data/images/captured",
        "data/videos/captured",
        "data/temp",
        "data/cache/camera",
        "data/logs",
        "data/database",
        "data/settings",
    ]

    # Create directories
    for dir_path in directories:
        full_path = root_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

        # Create __init__.py in Python packages
        if dir_path.startswith("src"):
            init_file = full_path / "__init__.py"
            init_file.touch(exist_ok=True)

    print("Project structure created successfully!")


if __name__ == "__main__":
    create_project_structure()
