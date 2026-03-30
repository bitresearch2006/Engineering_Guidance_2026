import os
import rasterio
import numpy as np
import torch
from torch.utils.data import Dataset

class VIEDataset(Dataset):
    def __init__(self, image_dir, label_dir, file_list, transform=None):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.files = file_list
        self.transform = transform

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        img_name = self.files[idx]

        # 👉 Map image → label
        label_idx = img_name.split("_")[0]
        label_name = f"{label_idx}.tif"

        img_path = os.path.join(self.image_dir, img_name)
        label_path = os.path.join(self.label_dir, label_name)

        # 🛰️ Read image
        with rasterio.open(img_path) as src:
            img = src.read()[:3]   # take 3 bands

        # 🧾 Read label
        with rasterio.open(label_path) as src:
            mask = src.read(1)

        # normalize image
        img = img.astype(np.float32)
        img = (img - img.min()) / (img.max() + 1e-6)

        # to tensor
        img = torch.tensor(img, dtype=torch.float32)
        mask = torch.tensor(mask, dtype=torch.long)

        if np.random.rand() > 0.5:
            img = np.flip(img, axis=2).copy()
            mask = np.flip(mask, axis=1).copy()

        return img, mask
