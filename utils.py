
import re, os, json
from PIL import Image
import exifread

def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()

def get_exif(path):
    with open(path, 'rb') as f:
        tags = exifread.process_file(f, details=False, strict=True)
    simple = {}
    for k, v in tags.items():
        simple[k] = str(v)
    return simple

def extract_xmp(bytes_data):
    try:
        s = bytes_data.find(b"<x:xmpmeta")
        if s == -1:
            s = bytes_data.find(b"<xmpmeta")
        if s == -1:
            return ""
        e = bytes_data.find(b"</x:xmpmeta>", s)
        if e == -1:
            e = bytes_data.find(b"</xmpmeta>", s)
        if e == -1:
            return ""
        block = bytes_data[s:e+12]
        return block.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def find_cc_license(xmp_text):
    if not xmp_text:
        return None
    m = re.search(r'(https?://creativecommons\.org/[^"\s<>]+)', xmp_text, re.IGNORECASE)
    if m:
        return m.group(1)
    m2 = re.search(r'(https?://creativecommons\.org/publicdomain/zero/1\.0/)', xmp_text, re.IGNORECASE)
    if m2:
        return m2.group(1)
    return None

def classify_from_cc_url(url):
    url_l = url.lower()
    if "publicdomain/zero" in url_l or "/cc0/" in url_l:
        return "CC0"
    if "/by-sa/" in url_l:
        return "CC BY-SA"
    if "/by-nd/" in url_l:
        return "CC BY-ND"
    if "/by-nc/" in url_l:
        return "CC BY-NC"
    if "/by/" in url_l:
        return "CC BY"
    return "Creative Commons (diğer)"

def normalize_signals(exif_dict, xmp_text):
    signals = {}
    for key in ["Image Copyright", "Image Artist", "Image XPAuthor"]:
        if key in exif_dict and exif_dict[key].strip():
            signals[key] = exif_dict[key].strip()
    if xmp_text:
        cc = find_cc_license(xmp_text)
        if cc:
            signals["XMP cc:license"] = cc
        ws = re.search(r'webstatementofrights[^>]*?>([^<]+)<', xmp_text, re.IGNORECASE)
        if ws:
            signals["XMP WebStatementOfRights"] = ws.group(1).strip()
        cr = re.search(r'<dc:creator[^>]*?>\s*<rdf:Seq>\s*<rdf:li>([^<]+)</rdf:li>', xmp_text, re.IGNORECASE|re.DOTALL)
        if cr:
            signals["XMP dc:creator"] = cr.group(1).strip()
    return signals

def heuristic_classify(signals):
    category = "Belirsiz"
    confidence = 0.2
    if "XMP cc:license" in signals:
        cc_class = classify_from_cc_url(signals["XMP cc:license"])
        category = cc_class
        confidence = 0.95
    elif "Image Copyright" in signals and signals["Image Copyright"]:
        category = "All Rights Reserved"
        confidence = 0.7
    return category, confidence

def action_suggestions(category):
    acts = []
    if category == "All Rights Reserved":
        acts.append("Kullanmayın: Telif sahibinden yazılı izin alın.")
    elif category == "Belirsiz":
        acts.append("Tersine görsel arama (TinEye/Google Lens/Yandex) ile orijinal kaynağı bulun.")
        acts.append("Kaynak sitede lisans şartlarını okuyun.")
    elif category.startswith("CC "):
        acts.append("Atıf metnini hazırlayın (Yazar, eser, lisans linki).")
        if category == "CC BY-ND":
            acts.append("Değişiklik yapmayın.")
        if category == "CC BY-NC":
            acts.append("Ticari kullanım yapmayın.")
    elif category == "CC0":
        acts.append("İsteğe bağlı atıf yapın; kanıt için kaynağı saklayın.")
    acts.append("Kaynak ve lisans sayfasını ekran görüntüsüyle arşivleyin.")
    return acts

def translate_bucket(category):
    bucket_map = {
        "All Rights Reserved": "All Rights Reserved (Tüm hakları saklıdır)",
        "CC BY": "CC BY",
        "CC BY-SA": "CC BY-SA",
        "CC BY-ND": "CC BY-ND",
        "CC BY-NC": "CC BY-NC",
        "CC0": "CC0 (Kamu malı)",
        "Belirsiz": "Belirsiz (Web eşlemesi gerekli)",
        "Creative Commons (diğer)": "Creative Commons (diğer)"
    }
    return bucket_map.get(category, category)

def analyze_image(path):
    data = read_bytes(path)
    exif = get_exif(path)
    xmp = extract_xmp(data)
    signals = normalize_signals(exif, xmp)
    category, confidence = heuristic_classify(signals)
    return {
        "file": os.path.basename(path),
        "category_raw": category,
        "category": translate_bucket(category),
        "confidence": round(confidence, 2),
        "signals": signals,
        "actions": action_suggestions(category)
    }
