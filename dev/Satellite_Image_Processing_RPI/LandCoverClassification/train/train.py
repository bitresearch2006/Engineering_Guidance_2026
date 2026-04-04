import os
import torch
import gc
import numpy as np
from torch.utils.data import DataLoader, random_split
import torch.nn as nn
import torch.optim as optim
from dataset_vie import VIEDataset
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt

torch.set_num_threads(2)

# ==============================
# PATHS
# ==============================
IMG_DIR = "/home/bitdev/sips/sentinel2-landcover-classification/data/vie/sentinel"
LBL_DIR = "/home/bitdev/sips/sentinel2-landcover-classification/data/vie/label/osm-multiclass"

# ==============================
# SIMPLE UNET
# ==============================
class SimpleUNet(nn.Module):
    def __init__(self, n_classes):
        super().__init__()

        self.enc1 = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(),
            nn.Conv2d(16, 16, 3, padding=1), nn.ReLU()
        )
        self.pool = nn.MaxPool2d(2)

        self.enc2 = nn.Sequential(
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.ReLU()
        )

        self.up = nn.Upsample(scale_factor=2, mode='bilinear')
        self.dec = nn.Sequential(
            nn.Conv2d(32, 16, 3, padding=1), nn.ReLU(),
            nn.Conv2d(16, n_classes, 1)
        )

    def forward(self, x):
        x1 = self.enc1(x)
        x2 = self.pool(x1)
        x3 = self.enc2(x2)
        x4 = self.up(x3)
        out = self.dec(x4)
        return out

# ==============================
# LOAD DATA
# ==============================
all_files = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".tif")])

files = []
missing_labels = []

for f in all_files:
    idx = f.split("_")[0]
    label_path = os.path.join(LBL_DIR, f"{idx}.tif")

    if os.path.exists(label_path):
        files.append(f)
    else:
        missing_labels.append(f)

print(f"✅ Valid samples: {len(files)}")
print(f"❌ Skipped (missing labels): {len(missing_labels)}")

dataset = VIEDataset(IMG_DIR, LBL_DIR, files)

# split 70/30
train_size = int(0.7 * len(dataset))
val_size = len(dataset) - train_size

train_ds, val_ds = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_ds, batch_size=1, shuffle=True, num_workers=0)
val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, num_workers=0)

# ==============================
# MODEL
# ==============================
device = "cpu"
model = SimpleUNet(n_classes=4).to(device)
weights = torch.tensor([3.0, 3.0, 1.0, 3.0]).to(device)
criterion = nn.CrossEntropyLoss(weight=weights)
optimizer = optim.Adam(model.parameters(), lr=1e-4)

# ==============================
# TRAIN
# ==============================
EPOCHS = 5

for epoch in range(EPOCHS):
    model.train()
    total_loss = 0

for imgs, masks in train_loader:
    imgs = imgs.to(device)
    masks = masks.to(device)

    optimizer.zero_grad()

    outputs = model(imgs)

    # 🔥 Normalize loss
    loss = criterion(outputs, masks) / masks.numel()

    loss.backward()
    optimizer.step()

    # 🔥 Free memory
    del imgs, masks, outputs

    total_loss += loss.item()

    print(f"Epoch {epoch+1}, Loss: {total_loss:.4f}")
gc.collect()
torch.cuda.empty_cache()

# ==============================
# EVALUATION
# ==============================
model.eval()
import numpy as np

num_classes = 4
cm = np.zeros((num_classes, num_classes), dtype=np.int64)

with torch.no_grad():
    for imgs, masks in val_loader:
        outputs = model(imgs)
        preds = torch.argmax(outputs, dim=1)

        preds = preds.cpu().numpy().flatten()
        masks = masks.cpu().numpy().flatten()

        for p, t in zip(preds, masks):
            if t < num_classes:
                cm[t, p] += 1

print("Confusion Matrix:\n", cm)

accuracy = np.trace(cm) / np.sum(cm)
print("Accuracy:", accuracy)

# ==============================
# SAVE MODEL
# ==============================
torch.save(model.state_dict(), "model_vie.pth")

print("✅ Model saved!")
