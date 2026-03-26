import socket
import ssl
import json
import base64
from io import BytesIO
from PIL import Image

import rasterio
import numpy as np

HOST = "bitresearch.bitone.in"
PORT = 443


def main():

    print("Connecting to FAAS gateway via HTTPS socket...")

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

    # Create socket
    sock = socket.create_connection((HOST, PORT))

    # Disable SSL verification (for testing)
    context = ssl._create_unverified_context()
    ssock = context.wrap_socket(sock)

    # Send request
    ssock.sendall(request.encode())

    # Receive response
    response = b""
    while True:
        data = ssock.recv(4096)
        if not data:
            break
        response += data

    ssock.close()

    response_text = response.decode(errors="ignore")

    # Separate headers and body
    body = response_text.split("\r\n\r\n", 1)[1]

    print("Received response body")

    # Parse JSON
    data = json.loads(body)

    if data["status"] != "success":
        print("Error:", data)
        return

    print("Image name:", data["image_name"])

    # Decode Base64 image
    img_bytes = base64.b64decode(data["content"])

    # Save TIFF file
    output_path = "output_faas.tif"

    with open(output_path, "wb") as f:
     f.write(img_bytes)

    print("TIFF file saved:", output_path)

    # Read using rasterio
    with rasterio.open(output_path) as src:
     img = src.read()   # (C, H, W)

    # Take first 3 bands (approx RGB)
    rgb = img[:3]

    # Convert (C,H,W) → (H,W,C)
    rgb = np.transpose(rgb, (1, 2, 0))

    # Normalize for display
    rgb = (rgb - rgb.min()) / (rgb.max() + 1e-6)
    rgb = (rgb * 255).astype(np.uint8)

    # Show using PIL
    Image.fromarray(rgb).show()

    print("RGB preview displayed!")

if __name__ == "__main__":
    main()