from pathlib import Path

def create_directories():
    # Create necessary directories
    directories = [
        "src",
        "src/ui",
        "src/core",
        "src/utils",
    ]
    
    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py files
        init_file = path / "__init__.py"
        init_file.touch(exist_ok=True)

if __name__ == "__main__":
    create_directories()