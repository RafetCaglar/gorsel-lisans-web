import re, os, json, urllib.parse, requests
from PIL import Image
import exifread
from dotenv import load_dotenv
from ajans_list import AJANS_VE_MEDYA_DOMAINS

load_dotenv()  # .env varsa anahtarları okuyalım

TINEYE_PUBLIC_KEY = os.getenv("TINEYE_PUBLIC_KEY")       # opsiyonel
TINEYE_PRIVATE_KEY = os.getenv("TINEYE_PRIVATE_KEY")     # opsiyonel
SERPAPI_KEY = os.getenv("SERPAPI_KEY")                   # opsiyonel

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
        acts.append("Tersine görsel arama (TinEye/Google Lens/SerpAPI) ile orijinal kaynağı bulun.")
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

# ---------- WEB EŞLEMESİ (OPSİYONEL) ----------
def domain_from_url(u):
    try:
        netloc = urllib.parse.urlparse(u).netloc.lower()
        if netloc.startswith("www."): netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

def ajans_eslestirme_from_domains(domains):
    hits = []
    for d in domains:
        d0 = d.lower()
        if d0.startswith("www."): d0 = d0[4:]
        for ajans_domain, label in AJANS_VE_MEDYA_DOMAINS.items():
            if d0.endswith(ajans_domain):
                hits.append((d0, label))
    return hits

def reverse_search_serpapi(image_url):
    """Google Görseller için SerpAPI kullanımı (opsiyonel anahtar gerektirir)."""
    if not SERPAPI_KEY:
        return {"provider": "serpapi", "enabled": False, "domains": [], "note": "SERPAPI_KEY yok"}
    try:
        # SerpAPI 'google_images' engine + image_url araması
        endpoint = "https://serpapi.com/search.json"
        params = {"engine": "google_images", "image_url": image_url, "api_key": SERPAPI_KEY}
        r = requests.get(endpoint, params=params, timeout=25)
        data = r.json()
        domains = []
        for itm in data.get("image_results", []):
            link = itm.get("link") or itm.get("source")
            if link:
                domains.append(domain_from_url(link))
        return {"provider": "serpapi", "enabled": True, "domains": list(dict.fromkeys(domains))}
    except Exception as e:
        return {"provider": "serpapi", "enabled": True, "error": str(e), "domains": []}

def reverse_search_tineye(image_url):
    """TinEye Search API (opsiyonel anahtar gerektirir)."""
    if not (TINEYE_PUBLIC_KEY and TINEYE_PRIVATE_KEY):
        return {"provider": "tineye", "enabled": False, "domains": [], "note": "TINEYE_PUBLIC_KEY/PRIVATE_KEY yok"}
    try:
        endpoint = "https://api.tineye.com/rest/search/"
        params = {"image_url": image_url}
        auth = (TINEYE_PUBLIC_KEY, TINEYE_PRIVATE_KEY)  # bazı planlarda Basic Auth
        r = requests.get(endpoint, params=params, auth=auth, timeout=25)
        data = r.json()
        results = data.get("result", {}).get("matches", [])
        domains = []
        for m in results:
            for b in m.get("backlinks", []):
                u = b.get("url")
                if u:
                    domains.append(domain_from_url(u))
        return {"provider": "tineye", "enabled": True, "domains": list(dict.fromkeys(domains))}
    except Exception as e:
        return {"provider": "tineye", "enabled": True, "error": str(e), "domains": []}


def analyze_image(path, public_base_url=None):
    """public_base_url: ör. https://<host>/  -> /uploads/... ile birleşip görseli dışarıya açık URL yapar."""
    data = read_bytes(path)
    exif = get_exif(path)
    xmp = extract_xmp(data)
    signals = normalize_signals(exif, xmp)
    category, confidence = heuristic_classify(signals)

    web_insight = {"note": "web eşlemesi kapalı"}
    ajans_hits = []

    # Otomatik web eşlemesi (anahtar eklenirse çalışır)
    if public_base_url:
        image_url = urllib.parse.urljoin(public_base_url, "uploads/" + os.path.basename(path))
        serp = reverse_search_serpapi(image_url)
        tine = reverse_search_tineye(image_url)
        collected_domains = []
        for prov in (serp, tine):
            if prov.get("domains"):
                collected_domains.extend(prov["domains"])
        collected_domains = list(dict.fromkeys([d for d in collected_domains if d]))
        if collected_domains:
            hits = ajans_eslestirme_from_domains(collected_domains)
            if hits:
                ajans_hits = [{"domain": d, "label": label} for d, label in hits]
                # Ajans bulunduysa pratikte teliflidir
                category = "All Rights Reserved"
                confidence = max(confidence, 0.9)
        web_insight = {"serpapi": serp, "tineye": tine, "domains": collected_domains}

    return {
        "file": os.path.basename(path),
        "category_raw": category,
        "category": translate_bucket(category),
        "confidence": round(confidence, 2),
        "signals": signals,
        "actions": action_suggestions(category),
        "web_insight": web_insight,
        "ajans_hits": ajans_hits
    }


def analyze_source_url(page_url):
    """Manuel yapıştırılan haber sayfası URL’sini alan adına göre hızlı sınıflandırır."""
    d = domain_from_url(page_url)
    hit = None
    if d:
        for ajans_domain, label in AJANS_VE_MEDYA_DOMAINS.items():
            if d.endswith(ajans_domain):
                hit = {"domain": d, "label": label}
                break
    return {
        "input": page_url,
        "domain": d,
        "ajans_match": hit,
        "category": translate_bucket("All Rights Reserved" if hit else "Belirsiz"),
        "suggest": "Ajans/medya eşleşti, telifli kabul edin." if hit else "Eşleşme yok; sayfada lisans şartlarını kontrol edin."
    }
