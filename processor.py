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
    # Streamlit Cloud runs on Linux (Debian)
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        return ImageFont.load_default()

def get_surrounding_paper_color(img, x, y, w, h):
    margin = 5
    img_w, img_h = img.size
    left, top = max(0, x - margin), max(0, y - margin)
    right, bottom = min(img_w, x + w + margin), min(img_h, y + h + margin)
    
    region = img.crop((left, top, right, bottom))
    quantized = region.quantize(colors=10, method=2)
    colors = quantized.getcolors()
    if not colors: return (255, 255, 255)

    sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
    palette = quantized.getpalette()

    for count, index in sorted_colors:
        r, g, b = palette[index*3], palette[index*3+1], palette[index*3+2]
        if (r + g + b) > 400: return (r, g, b)
    return (255, 255, 255)

def get_vision_client():
    """
    Detects if running locally (Env Var) or in Cloud (Streamlit Secrets).
    """
    # 1. Check Streamlit Secrets (Production)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return vision.ImageAnnotatorClient(credentials=creds)
    
    # 2. Fallback to Local Environment Variable
    return vision.ImageAnnotatorClient()

# --- MAIN LOGIC ---
def process_image(image_bytes):
    client = get_vision_client()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    
    boxes = []
    if response.full_text_annotation:
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for para in block.paragraphs:
                    for word in para.words:
                        text = "".join([s.text for s in word.symbols]).strip()
                        if not text: continue
                        v = word.bounding_box.vertices
                        xs, ys = [pt.x for pt in v], [pt.y for pt in v]
                        boxes.append({
                            "text": text,
                            "x": min(xs), "y": min(ys),
                            "w": max(xs) - min(xs), "h": max(ys) - min(ys)
                        })

    if not boxes: return None

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    heights = [b["h"] for b in boxes if b["h"] > 10]
    median_h = statistics.median(heights) if heights else 20
    font_size = int(median_h * 0.90)
    
    try:
        # Load font dynamically based on size
        # Note: In production we use DejaVu, locally it might fallback
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()

    pad = 2
    for b in boxes:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        bg_color = get_surrounding_paper_color(img, x, y, w, h)
        draw.rectangle((x-pad, y-pad, x+w+pad, y+h+pad), fill=bg_color)
        mid_x, mid_y = x + w/2, y + h/2
        draw.text((mid_x, mid_y), b["text"], font=font, fill="black", anchor="mm")

    return img