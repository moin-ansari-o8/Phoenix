import os
import logging
from pathlib import Path

# Setup logging to see what gets deleted
logging.basicConfig(level=logging.INFO, format="%(message)s")


def remove_empty_files(root_dir):
    """
    Recursively scans the root_dir and deletes any file that is exactly 0 bytes.
    Ignores critical system/environment directories like .git and .venv.
    """
    exclude_dirs = {".git", ".venv", "__pycache__", "node_modules"}
    deleted_count = 0

    logging.info(f"Scanning '{root_dir}' for empty files...\n")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Prevent os.walk from scanning excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            try:
                # If file size is exactly 0 bytes (empty)
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    logging.info(f"Deleted: {file_path}")
                    deleted_count += 1
            except FileNotFoundError:
                pass  # The file might have been removed already
            except Exception as e:
                logging.error(f"Error reading/deleting {file_path}: {e}")

    logging.info(
        f"\nCleanup Complete! Successfully deleted {deleted_count} empty files."
    )


if __name__ == "__main__":
    # Get the directory where this script is located (Phoenix root)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    remove_empty_files(current_dir)
