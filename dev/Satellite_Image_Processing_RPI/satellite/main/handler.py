import os
import random
from PIL import Image

def handle():
    image_folder = "images"

    image_files = [
        f for f in os.listdir(image_folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
    ]

    if not image_files:
        print("No images found.")
        return None

    random_image = random.choice(image_files)
    image_path = os.path.join(image_folder, random_image)

    print("Selected Image:", random_image)

    img = Image.open(image_path)
    return img