import os
os.environ["TORCHDYNAMO_DISABLE"] = "1"

import sys
sys.path.append(os.path.abspath("src"))  # should update with where sentinal repo

import torch
import numpy as np
import rasterio
import albumentations as A
import matplotlib.pyplot as plt
from PIL import Image

from src.train_segmentation import SegmentationModule
import configs.segmentation as cfg
from src.configs.segmentation import Config


# ==============================
# 🔧 CONFIG
# ==============================
CKPT_PATH = "ckpts/sentinel-segmentation/last-v1.ckpt"
TIFF_PATH = "data/small/sentinel/0_0.tif"

AOI = "small"
LABELS = "osm-multiclass"
MODEL = "efficientnet-unet-b5"


# ==============================
# 🧠 LOAD CONFIG
# ==============================
config: Config = cfg.BASE_CONFIG(model_name=MODEL)
config.datamodule.dataset_cfg.aoi = AOI
config.datamodule.dataset_cfg.label_map = LABELS
config.num_classes = 4
config.train.class_distribution = [0.25]*4


# ==============================
# 🧠 LOAD MODEL
# ==============================
print("Loading model...")

model = SegmentationModule.load_from_checkpoint(
    CKPT_PATH,
    config=config,
    weights_only=False,
    strict=False
)

# keep model as-is → use double input
model = model.double()
model.net = model.net.double()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

print("Model loaded!")


# ==============================
# 📥 LOAD TIFF
# ==============================
with rasterio.open(TIFF_PATH) as f:
    img = f.read().astype(np.float64)  # (C,H,W)

H, W = img.shape[1], img.shape[2]

# convert to HWC
img = np.transpose(img, (1, 2, 0))


# ==============================
# 🔧 TRANSFORM (MATCH TRAINING)
# ==============================
# 🔥 THIS is the key fix

mean = [775,1080,1228,2497,2204,1610]
std  = [1281,1270,1399,1368,1291,1154]

transform = A.Compose([
    A.Normalize(mean=mean, std=std)
])

transformed = transform(image=img)
img = transformed["image"]

# back to CHW
img = np.transpose(img, (2, 0, 1))


# ==============================
# 🔮 INFERENCE
# ==============================
x = torch.from_numpy(img).unsqueeze(0).double().to(device)

print("Input shape:", x.shape)

with torch.no_grad():
    output = model(x)
    pred = torch.argmax(output, dim=1)[0].cpu().numpy()

print("Prediction complete!")


# ==============================
# 🎨 COLOR MAP
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


# ==============================
# 💾 SAVE OUTPUT
# ==============================
os.makedirs("outputs", exist_ok=True)

colored = color_map(pred)
Image.fromarray(colored).save("outputs/pred_external.png")

print("Saved: outputs/pred_external.png")


# ==============================
# 🖼 VISUALIZATION
# ==============================
def to_rgb(img):
    blue = img[:,:,0]
    green = img[:,:,1]
    red = img[:,:,2]

    rgb = np.stack([red, green, blue], axis=-1)
    rgb = (rgb - rgb.min()) / (rgb.max() + 1e-6)
    return (rgb * 255).astype(np.uint8)


original = to_rgb(np.transpose(img, (1,2,0)))
overlay = (0.6 * original + 0.4 * colored).astype(np.uint8)

plt.figure(figsize=(12,4))

plt.subplot(1,3,1)
plt.title("Original")
plt.imshow(original)
plt.axis("off")

plt.subplot(1,3,2)
plt.title("Prediction")
plt.imshow(colored)
plt.axis("off")

plt.subplot(1,3,3)
plt.title("Overlay")
plt.imshow(overlay)
plt.axis("off")

plt.show()
