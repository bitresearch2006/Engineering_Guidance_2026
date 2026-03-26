import os
import sys
import json
import base64
from io import BytesIO
from PIL import Image

# Add the path to the 'main' directory so we can import handler.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main')))

from handler import handle


def main():

    print("Fetching random image...")

    response = handle("img")

    if not response:
        print("No response received")
        return

    # Convert JSON string to Python dict
    data = json.loads(response)

    if data["status"] != "success":
        print("Error:", data)
        return

    print("Image name:", data["image_name"])

    # Decode Base64 image
    img_bytes = base64.b64decode(data["content"])

    # Save TIFF file
    output_path = "output_test.tif"

    with open(output_path, "wb") as f:
     f.write(img_bytes)

    print("TIFF file saved successfully:", output_path)

if __name__ == "__main__":
    main()