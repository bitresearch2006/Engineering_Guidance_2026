# 🚀 Satellite Land Cover Classification (RPI + FaaS)

## 🧠 Overview
This system runs land cover classification on Raspberry Pi using:
- Satellite image from FaaS (JSON + base64 TIFF)
- Pretrained ML model (from cloned repo)
- Output images (original, prediction, overlay)
- Transfer results to Windows PC (SCP)

## 🔁 Runtime Flow
Every 10 seconds:
1. Call FaaS API
2. Receive satellite image (JSON)
3. Decode → TIFF
4. Run model
5. Generate output images
6. Save locally
7. Send to Windows PC

---

## 📁 Project Structure
Engineering_Guidance_2026/
└── dev/
    └── Satellite_Image_Processing_RPI/
        ├── build.gradle
        ├── settings.gradle
        └── LandCoverClassification/
            └── RPI/
                ├── main/
                │   └── handler.py
                └── sentinel2-landcover-classification/

---

## ⚙️ 1. Install Required Software

### On WSL / Raspberry Pi
```
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git gradle gdal-bin
```

### Python packages
```
pip install torch rasterio numpy pillow albumentations requests paramiko
```

---

## 📦 2. Setup Project

### Step 1
```
cd Engineering_Guidance_2026/dev/Satellite_Image_Processing_RPI
```

### Step 2
```
gradle getDeps
```

### Step 3
```
python3 -m venv venv
source venv/bin/activate
```

### Step 4
```
export PYTHONPATH=LandCoverClassification/RPI/sentinel2-landcover-classification
```

### Step 5
Ensure model exists:
```
LandCoverClassification/RPI/sentinel2-landcover-classification/ckpts/sentinel-segmentation/last-v1.ckpt
```

---

## 🌐 3. FaaS Configuration

POST https://bitresearch.bitone.in/function/satellite

Request:
```
{
  "arg": "img"
}
```

Response:
```
{
  "filename": "image.tif",
  "content": "<base64 encoded TIFF>"
}
```

---

## 🖥️ 4. Windows PC Setup

### Enable SSH
```
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
```

### Get IP
```
ipconfig
```

### Folder
```
C:\Users\<username>\Desktop\outputs\
```

---

## ▶️ 5. Start Application

```
cd LandCoverClassification/RPI/main
python handler.py
```

---

## 📦 Output

Raspberry Pi:
```
outputs/
 ├── original_<timestamp>.png
 ├── pred_<timestamp>.png
 ├── overlay_<timestamp>.png
```

Windows PC:
```
Desktop/outputs/
 ├── original_<timestamp>.png
 ├── pred_<timestamp>.png
 ├── overlay_<timestamp>.png
```

---

## ⚠️ Troubleshooting

Import error:
```
export PYTHONPATH=LandCoverClassification/RPI/sentinel2-landcover-classification
```

Gradle missing:
```
sudo apt install gradle
```

Network test:
```
ping <windows_ip>
```

---

## 🎯 Summary
- Clone dependency via Gradle
- Setup Python environment
- Run handler.py
- Automatic processing every 10 seconds
- Outputs saved and transferred to Windows
