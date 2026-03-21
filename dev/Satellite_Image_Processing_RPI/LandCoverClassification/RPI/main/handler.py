import os
import sys
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_PATH = os.path.join(BASE_DIR, "sentinel2-landcover-classification")
sys.path.append(REPO_PATH)
import io
import time
import base64
import requests
import numpy as np
import rasterio
import torch
import albumentations as A
from PIL import Image
import paramiko

from src.train_segmentation import SegmentationModule
import configs.segmentation as cfg


# ==============================
# 🔧 CONFIG
# ==============================
CKPT_PATH = "ckpts/sentinel-segmentation/last-v1.ckpt"
FAAS_URL = "https://bitresearch.bitone.in/function/satellite"

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🔹 SCP CONFIG
WINDOWS_IP = "192.168.1.10"
WINDOWS_USER = "your_username"
WINDOWS_PASSWORD = "your_password"
WINDOWS_DEST_PATH = "C:/Users/your_username/Desktop/outputs/"

INTERVAL = 10  # seconds


# ==============================
# 🧠 LOAD MODEL (ONCE)
# ==============================
print("Loading model...")

config = cfg.BASE_CONFIG(model_name="efficientnet-unet-b5")
config.datamodule.dataset_cfg.aoi = "small"
config.datamodule.dataset_cfg.label_map = "osm-multiclass"
config.num_classes = 4
config.train.class_distribution = [0.25]*4

model = SegmentationModule.load_from_checkpoint(
    CKPT_PATH,
    config=config,
    weights_only=False,
    strict=False
)

model = model.double()
model.net = model.net.double()

device = torch.device("cpu")
model.to(device)
model.eval()

print("Model loaded!")


# ==============================
# 🔧 NORMALIZATION
# ==============================
mean = [775,1080,1228,2497,2204,1610]
std  = [1281,1270,1399,1368,1291,1154]

transform = A.Compose([
    A.Normalize(mean=mean, std=std)
])


# ==============================
# 🎨 UTILS
# ==============================
def color_map(mask):
    colors = {
        0: (0, 0, 0),
        1: (255, 0, 0),
        2: (0, 255, 0),
        3: (0, 0, 255),
    }

    h, w = mask.shape
    colored = np.zeros((h, w, 3), dtype=np.uint8)

    for cls, color in colors.items():
        colored[mask == cls] = color

    return colored


def to_rgb(img):
    img = np.transpose(img, (1,2,0))
    rgb = img[:,:,:3]
    rgb = (rgb - rgb.min()) / (rgb.max() + 1e-6)
    return (rgb * 255).astype(np.uint8)


def send_via_scp(local_path, remote_path):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(WINDOWS_IP, username=WINDOWS_USER, password=WINDOWS_PASSWORD)

    sftp = ssh.open_sftp()
    sftp.put(local_path, remote_path)

    sftp.close()
    ssh.close()


# ==============================
# 🔁 MAIN LOOP
# ==============================
while True:
    try:
        print("\nFetching image from FaaS...")

        response = requests.post(FAAS_URL, json={"arg": "img"})
        if response.status_code != 200:
            print("FaaS error:", response.status_code)
            time.sleep(INTERVAL)
            continue

        data = response.json()

        # 🔥 decode base64
        img_bytes = base64.b64decode(data["content"])
        tiff_bytes = io.BytesIO(img_bytes)

        # ==============================
        # 📥 READ TIFF
        # ==============================
        with rasterio.open(tiff_bytes) as f:
            img = f.read().astype(np.float64)

        H, W = img.shape[1], img.shape[2]

        # ==============================
        # 🔧 TRANSFORM
        # ==============================
        img_hwc = np.transpose(img, (1,2,0))
        img_norm = transform(image=img_hwc)["image"]
        img_norm = np.transpose(img_norm, (2,0,1))

        # ==============================
        # 🔮 INFERENCE
        # ==============================
        x = torch.from_numpy(img_norm).unsqueeze(0).double().to(device)

        with torch.no_grad():
            output = model(x)
            pred = torch.argmax(output, dim=1)[0].cpu().numpy()

        print("Prediction done!")

        # ==============================
        # 🖼 OUTPUTS
        # ==============================
        original = to_rgb(img)
        pred_img = color_map(pred)
        overlay = (0.6 * original + 0.4 * pred_img).astype(np.uint8)

        timestamp = int(time.time())

        orig_path = f"{OUTPUT_DIR}/original_{timestamp}.png"
        pred_path = f"{OUTPUT_DIR}/pred_{timestamp}.png"
        overlay_path = f"{OUTPUT_DIR}/overlay_{timestamp}.png"

        Image.fromarray(original).save(orig_path)
        Image.fromarray(pred_img).save(pred_path)
        Image.fromarray(overlay).save(overlay_path)

        print("Saved locally!")

        # ==============================
        # 🚀 SCP TRANSFER
        # ==============================
        send_via_scp(orig_path, WINDOWS_DEST_PATH + f"original_{timestamp}.png")
        send_via_scp(pred_path, WINDOWS_DEST_PATH + f"pred_{timestamp}.png")
        send_via_scp(overlay_path, WINDOWS_DEST_PATH + f"overlay_{timestamp}.png")

        print("Sent to Windows PC!")

    except Exception as e:
        print("Error:", e)

    # ==============================
    # ⏱ WAIT
    # ==============================
    time.sleep(INTERVAL)
