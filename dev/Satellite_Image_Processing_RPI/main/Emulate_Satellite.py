import os, time, requests

SERVER = "http://127.0.0.1:5000"  # same PC server address
IMAGE_FOLDER = "sat_images"
INTERVAL = 5  # seconds between sends

def send_image(path):
    url = SERVER + "/upload_raw"
    files = {'image': open(path,'rb')}
    resp = requests.post(url, files=files)
    print("Sent:", path, "->", resp.status_code, resp.text)

def main():
    imgs = [os.path.join(IMAGE_FOLDER,f) for f in sorted(os.listdir(IMAGE_FOLDER)) if f.lower().endswith(('.jpg','.png','.jpeg','.tif'))]
    print("Found", len(imgs),"images")
    idx = 0
    while True:
        if not imgs:
            print("No images found, waiting...")
            time.sleep(5)
            continue
        p = imgs[idx % len(imgs)]
        try:
            send_image(p)
        except Exception as e:
            print("Error sending:", e)
        idx += 1
        time.sleep(INTERVAL)

if __name__=='__main__':
    main()
