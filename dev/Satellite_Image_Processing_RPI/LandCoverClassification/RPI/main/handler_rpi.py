import os
import socket
import ssl
import json
import base64

import torch
import numpy as np
import rasterio
from PIL import Image
import torch.nn as nn

# -----------------------------
# CONFIG
# -----------------------------
MODEL_PATH = "/home/pi/model_vie.pth"   # ⚠️ update path on Pi
OUTPUT_BASE_DIR = "outputs"
DEVICE = "cpu"

HOST = "bitresearch.bitone.in"
PORT = 443

# Reduce CPU threads (important for Pi)
torch.set_num_threads(1)

# Create output folder
IMAGE_FOLDER = os.path.join(OUTPUT_BASE_DIR, "Image_0")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

TIF_PATH = os.path.join(IMAGE_FOLDER, "input.tif")
RGB_PATH = os.path.join(IMAGE_FOLDER, "rgb_preview.png")
PRED_PATH = os.path.join(IMAGE_FOLDER, "prediction.png")


# -----------------------------
# MODEL
# -----------------------------
class SimpleUNet(nn.Module):
    def __init__(self, num_classes=4):
        super().__init__()

        self.enc1 = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 16, 3, padding=1),
            nn.ReLU()
        )

        self.pool = nn.MaxPool2d(2)

        self.enc2 = nn.Sequential(
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1),
            nn.ReLU()
        )

        self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)

        self.dec = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, num_classes, 1)
        )

    def forward(self, x):
        x1 = self.enc1(x)
        x2 = self.pool(x1)
        x3 = self.enc2(x2)
        x4 = self.up(x3)
        out = self.dec(x4)
        return out


# -----------------------------
# LOAD MODEL (safe for Pi)
# -----------------------------
print("🔄 Loading model...")
model = SimpleUNet(num_classes=4)

state_dict = torch.load(MODEL_PATH, map_location="cpu")
model.load_state_dict(state_dict)

model.to(DEVICE)
model.eval()
print("✅ Model loaded")


# -----------------------------
# FETCH IMAGE FROM FAAS (robust)
# -----------------------------
def fetch_image_from_faas(retries=3):
    print("🌐 Fetching image from FAAS...")

    body = json.dumps({"arg": "hello"})

    request = (
        "POST /function/satellite HTTP/1.1\r\n"
        f"Host: {HOST}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
        f"{body}"
    )

    for attempt in range(retries):
        try:
            sock = socket.create_connection((HOST, PORT), timeout=10)

            context = ssl._create_unverified_context()
            ssock = context.wrap_socket(sock)

            ssock.sendall(request.encode())

            response = b""
            while True:
                data = ssock.recv(4096)
                if not data:
                    break
                response += data

            ssock.close()

            response_text = response.decode(errors="ignore")
            body = response_text.split("\r\n\r\n", 1)[1]

            data = json.loads(body)

            if data["status"] != "success":
                raise Exception(data)

            img_bytes = base64.b64decode(data["content"])

            with open(TIF_PATH, "wb") as f:
                f.write(img_bytes)

            print("✅ TIFF saved")
            return

        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed:", e)

    raise RuntimeError("❌ Failed to fetch image from FAAS")


fetch_image_from_faas()


# -----------------------------
# LOAD IMAGE (memory safe)
# -----------------------------
with rasterio.open(TIF_PATH) as src:
    img = src.read(out_dtype=np.float32)  # avoids extra casting

# -----------------------------
# RGB PREVIEW
# -----------------------------
rgb = img[:3]
rgb = np.transpose(rgb, (1, 2, 0))

rgb = (rgb - rgb.min()) / (rgb.max() + 1e-6)
rgb_uint8 = (rgb * 255).astype(np.uint8)

Image.fromarray(rgb_uint8).save(RGB_PATH)
print("✅ RGB preview saved")


# -----------------------------
# PREPARE INPUT
# -----------------------------
img_model = img[:3]
img_model = img_model / (img_model.max() + 1e-6)

img_tensor = torch.from_numpy(img_model).unsqueeze(0)

# -----------------------------
# PREDICTION (optimized)
# -----------------------------
with torch.no_grad():
    output = model(img_tensor)
    pred = torch.argmax(output, dim=1).squeeze().numpy()

print("✅ Prediction done")


# -----------------------------
# COLOR MAP
# -----------------------------
color_map = {
    0: [255, 0, 0],
    1: [0, 0, 255],
    2: [0, 255, 0],
    3: [255, 255, 0]
}

h, w = pred.shape
color_img = np.zeros((h, w, 3), dtype=np.uint8)

for cls, color in color_map.items():
    color_img[pred == cls] = color

Image.fromarray(color_img).save(PRED_PATH)

print("✅ Segmentation saved")
print("🎉 Done! Output folder:", IMAGE_FOLDER)
