import os
import random
import json
import base64
from PIL import Image
from io import BytesIO


def handle(arg=None):

    try:
        # Locate images folder relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_folder = os.path.join(base_dir, "images")

        if not os.path.exists(image_folder):
            return json.dumps({
                "status": "error",
                "message": "images folder not found",
                "path": image_folder
            })

        image_files = [
            f for f in os.listdir(image_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        if not image_files:
            return json.dumps({
                "status": "error",
                "message": "No images found"
            })

        # Select random image
        random_image = random.choice(image_files)
        image_path = os.path.join(image_folder, random_image)

        img = Image.open(image_path)

        # Convert image to Base64
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()

        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        return json.dumps({
            "status": "success",
            "image_name": random_image,
            "image": img_base64
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        })