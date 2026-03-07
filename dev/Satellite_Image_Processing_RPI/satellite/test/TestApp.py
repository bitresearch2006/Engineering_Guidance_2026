import os
import sys

# Add the path to the 'main' directory so we can import handler.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main')))

from handler import handle

def main():

    print("Fetching random image...")

    img = handle()

    if img:
        print("Image loaded successfully.")
        img.show()
    else:
        print("Failed to load image.")

if __name__ == "__main__":
    main()