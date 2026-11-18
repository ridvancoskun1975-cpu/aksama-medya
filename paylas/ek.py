"""Ek gönderiler: günlük menünün dışındaki onaylı kaydırmalı gönderiler (ör. tanıtım; Rıdvan 16 Kas 19:15:
"tanıtım postu özel olur ayda bir olur veya isteyince olur."). Reel işinin son adımı (reel.yml) çalıştırır;
Google dış tetiği reel işini 09:20'de başlattığı için ek gönderi tarayıcısız, günün gönderisinden ve reel'den
sonra çıkar.

  python3 paylas/ek.py            vakti gelmiş, paylaşılmamış ek/<ad>/ gönderileri (KIP=prova|yayin)
  python3 paylas/ek.py denetle    yalnız onay ve dosya denetimi (Instagram'a gitmez)

ek/<ad>/: ek.json (tarih, alt_metinler), onay.json (aksama-bot'taki onayın aynısı), aciklama.txt, kareler/*.jpg.
Onay: karelerin ve açıklamanın özeti onay.json'dakiyle aynı olmalı (aksama-bot/uretim/ortak.py icerik_ozeti).
Görsel adresi açık depodaki dosyanın bu kayda ait ham adresi (raw.githubusercontent.com).
Kilitler: kayıt etiketi ek/<ad> + Instagram'daki son paylaşımlarda aynı ilk satırlı kaydırmalı gönderi.
Yayın kipinde: tarih gelmeden, o günün sabah gönderisi (paylasildi/<bugün>) çıkmadan ve 09:20–20:00 dışında
paylaşılmaz. Bir hata reel'i etkilemez (reel önceki adımda paylaşılmış olur); iş kırmızı biter ve ertesi
günün reel işinde yeniden denenir.
"""
import datetime as dt
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402  (Graph API yardımcıları)
import hikaye as H  # noqa: E402  (etiket okuma ve yazma)

KOK = pathlib.Path(__file__).resolve().parent.parent
DEPO = os.environ.get("GITHUB_REPOSITORY", "ridvancoskun1975-cpu/aksama-medya")
IST = P.IST
YASAK = (dt.time(8, 0), dt.time(9, 20))     # sabah gönderisi ve reel korunur
SAAT_SON = dt.time(20, 0)                   # ek gönderi akşam 20:00'den sonra çıkmaz
SURE = 15 * 60
BOYUT = (1080, 1350)


def ozet(m):
    print(m, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(m + "\n")


def ekler():
    return sorted(p.parent for p in (KOK / "ek").glob("*/ek.json"))


def oku(klasor):
    """ek.json + onay.json + açıklama; sorun varsa P.Dur."""
    e = json.loads((klasor / "ek.json").read_text(encoding="utf-8"))
    o = json.loads((klasor / "onay.json").read_text(encoding="utf-8"))
    sorun = []
    if e.get("ad") != klasor.name:
        sorun.append("ek.json ad alanı klasör adıyla aynı değil")
    try:
        dt.date.fromisoformat(e.get("tarih", ""))
    except ValueError:
        sorun.append("ek.json tarih YYYY-AA-GG olmalı")
    kareler, acik = o.get("kareler") or [], o.get("aciklama") or ""
    if not 2 <= len(kareler) <= 10:
        sorun.append("kaydırmalı gönderide 2–10 kare olmalı")
    for k in kareler:
        yol = klasor / k
        if not yol.is_file():
            sorun.append(f"{k} yok")
            continue
        if P.jpeg_bilgisi(yol) != BOYUT:
            sorun.append(f"{k} 1080×1350 JPEG değil")
        if yol.stat().st_size > P.KARE_BOYUT_EN_COK:
            sorun.append(f"{k} 8 MB'tan büyük")
    if not (klasor / acik).is_file():
        sorun.append("açıklama dosyası yok")
    if sorun:
        raise P.Dur(f"ek/{klasor.name}: " + "; ".join(sorun))
    metin = (klasor / acik).read_text(encoding="utf-8").strip()
    onay = o.get("onay") or {}
    ozet_simdi = P.icerik_ozeti(klasor, kareler, acik)
    if not onay.get("soz") or onay.get("ozet") != ozet_simdi or o.get("ozet") != ozet_simdi:
        sorun.append("onay yok ya da kareler/açıklama onaydan sonra değişmiş (özet tutmuyor)")
    if len(metin) > P.ACIKLAMA_EN_COK:
        sorun.append(f"açıklama {len(metin)} harf (en çok {P.ACIKLAMA_EN_COK})")
    if P.etiket_sayisi(metin) > P.ETIKET_EN_COK:
        sorun.append(f"açıklamada {P.etiket_sayisi(metin)} etiket (en çok {P.ETIKET_EN_COK})")
    if P.YZ_SATIRI not in metin:
        sorun.append("YZ satırı yok")
    alt = e.get("alt_metinler")
    if alt is not None and len(alt) != len(kareler):
        sorun.append("alt_metinler kare sayısıyla aynı uzunlukta olmalı")
    if sorun:
        raise P.Dur(f"ek/{klasor.name}: " + "; ".join(sorun))
    return {"ad": klasor.name, "tarih": dt.date.fromisoformat(e["tarih"]), "kareler": kareler,
            "aciklama": metin, "alt": alt or [None] * len(kareler), "onay": onay["soz"]}


def onceden_var(ilk):
    """Son paylaşımlarda (tarihe bakmadan) aynı ilk satırlı kaydırmalı gönderi var mı? Döner: medya kimliği ya da None."""
    r = P.graph("GET", f"{P.IG_ID}/media", {"fields": "id,caption,media_type,timestamp", "limit": "25"})
    for m in r.get("data", []):
        if m.get("media_type") == "CAROUSEL_ALBUM" and P.ilk_satir(m.get("caption")) == ilk:
            return m["id"]
    return None


def adres(ad, dosya, kayit):
    return f"https://raw.githubusercontent.com/{DEPO}/{kayit}/ek/{ad}/{dosya}"


def kap_kur(d, son):
    kayit = os.environ.get("GITHUB_SHA") or "main"
    cocuklar = []
    for k, a in zip(d["kareler"], d["alt"]):
        prm = {"image_url": adres(d["ad"], k, kayit), "is_carousel_item": "true", "alt_text": a}
        cocuklar.append(P.dayanikli("kare kabı", lambda prm=prm: P.graph("POST", f"{P.IG_ID}/media", prm)["id"], son))
    P.hazir_bekle(cocuklar, son)
    prm = {"media_type": "CAROUSEL", "children": ",".join(cocuklar), "caption": d["aciklama"]}
    if (os.environ.get("YZ_ETIKETI") or "hayir").strip().lower() == "evet":
        prm["is_ai_generated"] = "true"
    kap = P.dayanikli("gönderi kabı", lambda: P.graph("POST", f"{P.IG_ID}/media", prm)["id"], son)
    P.hazir_bekle([kap], son)
    return kap


def bir_ek(klasor, kip, simdi):
    """Döner: 'paylasildi' | 'prova' | 'onceden' | 'vakti-yok' | 'sabah-yok'."""
    d = oku(klasor)
    etiket = f"ek/{d['ad']}"
    ilk = P.ilk_satir(d["aciklama"])
    if kip == "yayin":
        if H.etiket_var(etiket):
            return "onceden"
        if simdi.date() < d["tarih"]:
            ozet(f"ek/{d['ad']}: paylaşım günü {d['tarih']:%d.%m.%Y}; bugün değil.")
            return "vakti-yok"
        if not H.etiket_var(f"paylasildi/{simdi.date().isoformat()}"):
            ozet(f"ek/{d['ad']}: bugünün gönderisi henüz çıkmadı; ek gönderi ondan sonra.")
            return "sabah-yok"
    son = P.zaman() + SURE
    if kip == "yayin":
        var = P.dayanikli("önceki paylaşım denetimi", lambda: onceden_var(ilk), son)
        if var:
            H.etiket_yaz(etiket, f"media {var} (Instagram'da önceden paylaşılmış bulundu)")
            ozet(f"ek/{d['ad']}: Instagram'da zaten var; yeniden paylaşılmadı.")
            return "onceden"
    kap = kap_kur(d, son)
    if kip != "yayin":
        ozet(f"Prova: ek/{d['ad']} ({len(d['kareler'])} kare) Instagram'a yüklendi ve hazır, **paylaşılmadı**.")
        return "prova"
    sonuc = P.paylas_dayanikli(kap, simdi.date(), ilk, son)
    mid = sonuc["id"]
    try:
        m = P.graph("GET", mid, {"fields": "permalink,timestamp"})
    except P.GraphHatasi:
        m = {}
    yazildi = H.etiket_yaz(etiket, f"media {mid} {m.get('permalink', '')} {m.get('timestamp', '')}".strip())
    ozet(f"**Ek gönderi paylaşıldı** ek/{d['ad']} {P.simdi():%H:%M}: {m.get('permalink', mid)}"
         + (" (önceki denemede gitmiş)" if sonuc.get("_onceden") else ""))
    if not yazildi:
        raise P.Dur(f"ek/{d['ad']} paylaşıldı ama kayıt etiketi yazılamadı; yeniden çalıştırmadan önce etiket elle yazılmalı.")
    return "paylasildi"


def calistir(simdi=None):
    kip = (os.environ.get("KIP") or "prova").strip()
    if kip not in ("prova", "yayin"):
        raise P.Dur(f"Bilinmeyen kip: {kip}")
    simdi = simdi or dt.datetime.now(IST)
    if YASAK[0] <= simdi.time() < YASAK[1]:
        ozet("Ek gönderi 08:00–09:20 arasında çalışmaz (sabah gönderisi ve reel korunur).")
        return []
    if kip == "yayin" and simdi.time() >= SAAT_SON:
        ozet(f"Ek gönderi {SAAT_SON:%H:%M}'den sonra paylaşılmaz; ertesi gün denenir.")
        return []
    sonuc = []
    for k in ekler():
        sonuc.append((k.name, bir_ek(k, kip, simdi)))
    if not sonuc:
        ozet("Ek gönderi yok.")
    return sonuc


def denetle():
    for k in ekler():
        d = oku(k)
        print(f"ek/{d['ad']}: {len(d['kareler'])} kare, {len(d['aciklama'])} harf, paylaşım günü {d['tarih']}, onay: {d['onay']}")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["denetle"]:
            denetle()
        elif not sys.argv[1:]:
            calistir()
        else:
            raise SystemExit(__doc__)
    except P.Dur as e:
        print(f"::error::{e}", flush=True)
        ozet(f"**Durdu:** {e}")
        sys.exit(1)
