# Görsel Lisans Denetleyici — Web UI

Basit bir Flask arayüzü ile görsel yükleyip lisans sinyallerini sınıflandırır.

## Kurulum
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma
```bash
python app.py
# Tarayıcı: http://localhost:5000
```

## Notlar
- Bu sürüm yalnızca yerel meta veriyi (EXIF/XMP/IPTC) okur.
- Tersine görsel arama (TinEye/Openverse) entegrasyon noktası için `utils.py` içinde fonksiyon kancaları ayrılabilir.