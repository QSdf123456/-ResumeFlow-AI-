#!/usr/bin/env python3
"""
ArtiFlow Studio – شركة AI ذاتية التشغيل بالكامل
توليد فن رقمي ← رفعه على Gumroad ← نشره على Blogger
"""

import os
import sys
import subprocess
import json
import time
import requests
import random
import pickle
from pathlib import Path

# ---------- مكتبات إضافية تحتاج تثبيتها ----------
# pip install google-api-python-client google-auth-oauthlib

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# =================== إعداداتك الخاصة – املأها ===================
GUMROAD_ACCESS_TOKEN = "اكتب_رمز_Gumroad_الخاص_بك"
GUMROAD_DOMAIN = "اسم_متجرك.gumroad.com"
PRICE_CENTS = 999          # السعر بالسنت (9.99$)

BLOGGER_CLIENT_ID = "اكتب_client_id"
BLOGGER_CLIENT_SECRET = "اكتب_client_secret"
BLOGGER_BLOG_ID = "اكتب_رقم_مدونتك"

FOOOCUS_PATH = r"C:\Fooocus"   # مسار مجلد Fooocus عندك (عدّله حسب نظامك)
OUTPUT_DIR = os.path.join(FOOOCUS_PATH, "outputs")

# إعدادات الجيل
IMAGES_PER_RUN = 3
# ===============================================================

SCOPES = ['https://www.googleapis.com/auth/blogger']

# ---------- بنك بسيط من الأفكار الفنية ----------
PROMPT_IDEAS = [
    "Epic fantasy landscape, trending on ArtStation, 8k",
    "Minimalist cyberpunk city, neon rain, high detail",
    "Watercolor floral bouquet, soft pastels, botanical illustration",
    "Surreal astronaut floating in space with galaxy inside helmet",
    "Geometric abstract composition, vibrant colors, modern art",
    "Japanese zen garden at sunrise, 4k wallpaper",
    "Cute kawaii coffee cup character, vector art style",
    "Vintage travel poster of Morocco, retro typography",
    "Futuristic eco-architecture, solarpunk, nature meets tech",
    "Oil painting of a majestic lion, golden ratio composition"
]

def generate_random_prompt():
    style = random.choice(["digital art", "oil painting", "watercolor", "vector", "photorealistic"])
    base = random.choice(PROMPT_IDEAS)
    return f"{base}, {style}, ultra detailed, 8k"

def run_fooocus(prompt, index):
    """تشغيل Fooocus عبر سطر الأوامر لإنتاج صورة واحدة"""
    out_path = os.path.join(OUTPUT_DIR, f"art_{index}_{int(time.time())}.png")
    cmd = [
        sys.executable, "entry_with_update.py",
        "--prompt", prompt,
        "--output-path", out_path,
        "--preset", "realistic",
        "--disable-image-prompt",
        "--disable-seed-increment",
    ]
    result = subprocess.run(cmd, cwd=FOOOCUS_PATH, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Fooocus خطأ: {result.stderr}")
        return None
    time.sleep(2)
    list_of_files = list(Path(out_path).parent.glob("*.png"))
    if not list_of_files:
        return None
    latest = max(list_of_files, key=lambda f: f.stat().st_mtime)
    return str(latest)

def create_gumroad_product(title, description, image_path):
    """إنشاء منتج على Gumroad ورفع الملف الرقمي (الصورة)"""
    headers = {"Authorization": f"Bearer {GUMROAD_ACCESS_TOKEN}"}
    payload = {
        "name": title,
        "description": description,
        "price": PRICE_CENTS,
    }
    r = requests.post("https://api.gumroad.com/v2/products", data=payload, headers=headers)
    if r.status_code != 200 and r.status_code != 201:
        print(f"Gumroad create product failed: {r.text}")
        return None
    product_id = r.json()["product"]["id"]

    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/png")}
        up = requests.put(
            f"https://api.gumroad.com/v2/products/{product_id}/file",
            files=files,
            headers=headers,
        )
    if up.status_code in [200, 201, 204]:
        print(f"تم رفع المنتج: {title} (ID: {product_id})")
        return product_id
    else:
        print(f"فشل رفع الملف: {up.text}")
        return None

def blogger_authenticate():
    """مصادقة Blogger API وإعادة الخدمة"""
    creds = None
    token_file = "blogger_token.pickle"
    if os.path.exists(token_file):
        with open(token_file, "rb") as tk:
            creds = pickle.load(tk)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": BLOGGER_CLIENT_ID,
                        "client_secret": BLOGGER_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"]
                    }
                },
                SCOPES,
            )
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as tk:
            pickle.dump(creds, tk)
    return build('blogger', 'v3', credentials=creds)

def post_to_blogger(title, content):
    """نشر مقال على Blogger"""
    service = blogger_authenticate()
    post = {
        "title": title,
        "content": content,
    }
    result = service.posts().insert(blogId=BLOGGER_BLOG_ID, body=post).execute()
    print(f"تم نشر التدوينة: {result['url']}")
    return result.get('url')

def main():
    print("===== ArtiFlow Studio جاري تشغيل =====")
    if not os.path.exists(FOOOCUS_PATH):
        print("خطأ: مسار Fooocus غير موجود، تأكد من FOOOCUS_PATH")
        return

    for i in range(IMAGES_PER_RUN):
        prompt = generate_random_prompt()
        title = f"Art Print - {prompt[:50]}..."
        desc = f"AI-generated fine art print. Style: {prompt}. High resolution, perfect for printing or digital display."

        print(f"توليد الصورة {i+1}...")
        image_path = run_fooocus(prompt, i+1)
        if not image_path:
            print("تخطي بسبب فشل التوليد")
            continue

        gum_id = create_gumroad_product(title, desc, image_path)
        if not gum_id:
            continue

        blog_title = f"New Art Print: {title}"
        blog_body = f"<p>{desc}</p><p>Get it here: <a href='https://{GUMROAD_DOMAIN}/l/{gum_id}'>Download Now</a></p>"
        post_to_blogger(blog_title, blog_body)

        time.sleep(5)

    print("===== انتهى التشغيل اليومي =====")

if __name__ == "__main__":
    main()