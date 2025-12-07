import io
import statistics
import platform
import os
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from google.cloud import vision
from google.oauth2 import service_account

# --- HELPERS ---
def get_font():
    print("[LOG] get_font called")
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        print("[LOG] Loaded DejaVuSans.ttf font")
        return font
    except Exception as e:
        print(f"[LOG] Failed to load DejaVuSans.ttf font: {e}")
        return ImageFont.load_default()

def get_surrounding_paper_color(img, x, y, w, h):
    print(f"[LOG] get_surrounding_paper_color called with x={x}, y={y}, w={w}, h={h}")
    margin = 5
    img_w, img_h = img.size
    left, top = max(0, x - margin), max(0, y - margin)
    right, bottom = min(img_w, x + w + margin), min(img_h, y + h + margin)
    print(f"[LOG] Cropping region: left={left}, top={top}, right={right}, bottom={bottom}")
    region = img.crop((left, top, right, bottom))
    quantized = region.quantize(colors=10, method=2)
    colors = quantized.getcolors()
    if not colors: 
        print("[LOG] No colors found, returning white")
        return (255, 255, 255)

    sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
    palette = quantized.getpalette()

    for count, index in sorted_colors:
        r, g, b = palette[index*3], palette[index*3+1], palette[index*3+2]
        if (r + g + b) > 400: 
            print(f"[LOG] Selected color: {(r, g, b)}")
            return (r, g, b)
    print("[LOG] No bright color found, returning white")
    return (255, 255, 255)

def get_vision_client():
    print("[LOG] get_vision_client called")
    # 1. Check Streamlit Secrets (Production)
    if "gcp_service_account" in st.secrets:
        print("[LOG] Using credentials from Streamlit secrets")
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return vision.ImageAnnotatorClient(credentials=creds)
    print("[LOG] Using default credentials")
    # 2. Fallback to Local Environment Variable
    return vision.ImageAnnotatorClient()

# --- MAIN LOGIC ---
def process_image(image_bytes):
    print("[LOG] process_image called")
    client = get_vision_client()
    image = vision.Image(content=image_bytes)
    print("[LOG] Sending image to Google Vision API")
    response = client.document_text_detection(image=image)
    print("[LOG] Received response from Vision API")
    
    boxes = []
    if response.full_text_annotation:
        print("[LOG] Found full_text_annotation")
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for para in block.paragraphs:
                    for word in para.words:
                        text = "".join([s.text for s in word.symbols]).strip()
                        if not text: continue
                        v = word.bounding_box.vertices
                        xs, ys = [pt.x for pt in v], [pt.y for pt in v]
                        box = {
                            "text": text,
                            "x": min(xs), "y": min(ys),
                            "w": max(xs) - min(xs), "h": max(ys) - min(ys)
                        }
                        print(f"[LOG] Detected word box: {box}")
                        boxes.append(box)

    if not boxes: 
        print("[LOG] No boxes found, returning None")
        return None

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    heights = [b["h"] for b in boxes if b["h"] > 10]
    median_h = statistics.median(heights) if heights else 20
    print(f"[LOG] Calculated median height: {median_h}")
    font_size = int(median_h * 0.90)
    print(f"[LOG] Calculated font size: {font_size}")
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        print("[LOG] Loaded DejaVuSans.ttf font with size", font_size)
    except Exception as e:
        print(f"[LOG] Failed to load DejaVuSans.ttf font: {e}")
        font = ImageFont.load_default()

    pad = 2
    for b in boxes:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        print(f"[LOG] Drawing box for text '{b['text']}' at ({x},{y},{w},{h})")
        bg_color = get_surrounding_paper_color(img, x, y, w, h)
        draw.rectangle((x-pad, y-pad, x+w+pad, y+h+pad), fill=bg_color)
        mid_x, mid_y = x + w/2, y + h/2
        draw.text((mid_x, mid_y), b["text"], font=font, fill="black", anchor="mm")

    print("[LOG] Finished drawing all boxes and text")
    return img