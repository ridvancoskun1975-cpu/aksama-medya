#!/usr/bin/env python3
"""Akşama Ne Var? (@aksama.ne.var) günlük paylaşım işi. Yalnız standart kütüphane.

İki adım (iş akışı .github/workflows/paylas.yml):
  hazirla  kip ve tarih; kilitler; anahtar ve hesap denetimi; özel depodan (aksama-bot) yalnız günün klasörü;
           paylaşım denetimi (onay, özet, kare, açıklama); Pages için _site klasörü.
  yayinla  kareler yayında mı; Instagram kapları; prova ise burada durur; yayin ise 09:00'ı bekler,
           iki kilit, paylaşım, kayıt etiketi (paylasildi/<tarih>).

Kipler:
  kontrol  yalnız denetim (Instagram'a yazmaz, Pages'e yüklemez)
  prova    paylaşım dışında her şey: kareler Pages'e çıkar, Instagram kapları hazırlanır, paylaşılmaz
           (kaplar 24 saatte kendiliğinden silinir)
  yayin    gerçek paylaşım; yalnız depo değişkeni PAYLASIM_KIPI=yayin iken (Rıdvan'ın açık onayı)

Açık depodur: günlüğe anahtar, açıklama metni ve menü yazılmaz; yalnız sayılar ve durum.
"""
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------- Ayarlar ----------
HESAP_ADI = "aksama.ne.var"
IG_ID = "17841474308613858"                 # @aksama.ne.var Instagram hesap kimliği (gizli değil)
BOT_DEPO = "ridvancoskun1975-cpu/aksama-bot"
GRAPH = os.environ.get("GRAPH_ADRESI", "https://graph.facebook.com/v26.0")
GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")

IST = dt.timezone(dt.timedelta(hours=3))    # Türkiye'de yaz saati yok
SAAT_HEDEF = dt.time(9, 0)                  # paylaşım saati
SAAT_ERKEN = dt.time(7, 30)                 # yayin bundan önce başlamaz
SAAT_SON = dt.time(16, 0)                   # bundan sonra o günün menüsü paylaşılmaz (Claude önerisi)
YASAK = (dt.time(8, 0), dt.time(9, 20))     # bu arada elle kontrol/prova yapılmaz (09:00 korunur)
DENEME_SURESI = 150 * 60                    # geçici hatada en çok 150 dk yeniden dener (yayın öncesi)
YAYINDA_SURESI = 15 * 60                    # kareler en çok 15 dk içinde Pages'te görünmeli
STOK_BAKIS = 14                             # stok için bakılan gün sayısı

# Paylaşım sınırları (Meta belgesi; aynı değerler aksama-bot/uretim/ortak.py içinde)
GEN, YUK = 1080, 1350
KARE_EN_AZ, KARE_EN_COK = 2, 10
ACIKLAMA_EN_COK = 2200
ETIKET_EN_COK = 5
KARE_BOYUT_EN_COK = 8 * 1024 * 1024

KIPLER = ("kontrol", "prova", "yayin")
TARIH_KALIBI = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TOKEN = os.environ.get("IG_TOKEN", "")
BOT_OKUMA = os.environ.get("BOT_OKUMA", "")
DURUM = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "aksama-paylasim.json"
SITE = pathlib.Path(os.environ.get("SITE_KLASORU", "_site"))


# ---------- Saat ve uyku (denemede değiştirilir) ----------
def simdi():
    return dt.datetime.now(IST)


def zaman():
    return time.monotonic()


def uyu(sn):
    time.sleep(sn)


# ---------- Günlük ----------
class Dur(Exception):
    """İş kırmızı biter (Rıdvan'a GitHub e-postası gider)."""


class Bitti(Exception):
    """Yapılacak iş yok; iş yeşil biter."""


def bilgi(m):
    print(m, flush=True)


def uyari(m):
    print(f"::warning::{m}", flush=True)


def ozet(m):
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(m + "\n")
    bilgi(m)


def cikti(ad, deger):
    yol = os.environ.get("GITHUB_OUTPUT")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(f"{ad}={deger}\n")


# ---------- Instagram (Graph API) ----------
GECICI_KODLAR = {1, 2, 4, 17, 32, 341, 613, 9004, 9007}
HAZIR_DEGIL_ALT = {2207027}                  # "Media not ready"
SINIR_ALT = {2207042}                        # günlük paylaşım sınırı doldu (geçici sayılmaz)


class GraphHatasi(Exception):
    def __init__(self, durum, govde, ag=False):
        hata = (govde or {}).get("error", {}) if isinstance(govde, dict) else {}
        self.durum, self.ag = durum, ag
        self.kod = hata.get("code")
        self.alt_kod = hata.get("error_subcode")
        self.gecici_bayrak = bool(hata.get("is_transient"))
        self.mesaj = hata.get("error_user_msg") or hata.get("message") or str(govde)[:200]
        super().__init__(self.kisa())

    def kisa(self):
        if self.ag:
            return f"ağ hatası: {self.mesaj}"
        return f"HTTP {self.durum}, kod {self.kod}/{self.alt_kod}: {self.mesaj}"

    def gecici(self):
        if self.alt_kod in SINIR_ALT:
            return False
        return (self.ag or (self.durum or 0) >= 500 or self.gecici_bayrak
                or self.kod in GECICI_KODLAR or self.alt_kod in HAZIR_DEGIL_ALT)

    def hazir_degil(self):
        return self.kod == 9007 or self.alt_kod in HAZIR_DEGIL_ALT


def graph(yontem, yol, params=None, zaman_asimi=60):
    params = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{GRAPH}/{yol}"
    basliklar = {"Authorization": f"Bearer {TOKEN}"}
    veri = None
    if yontem == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        veri = urllib.parse.urlencode(params).encode()
        basliklar["Content-Type"] = "application/x-www-form-urlencoded"
    istek = urllib.request.Request(url, data=veri, headers=basliklar, method=yontem)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            govde = json.loads(e.read().decode())
        except Exception:
            govde = {"error": {"message": f"HTTP {e.code}"}}
        raise GraphHatasi(e.code, govde)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise GraphHatasi(None, {"error": {"message": str(e)[:200]}}, ag=True)


def bekleme_suresi(deneme, hata=None):
    if hata is not None and hata.hazir_degil():
        return 30
    return (60, 120, 300, 600)[min(deneme, 3)]


def dayanikli(is_adi, fn, son_zaman):
    """Geçici hatada bekleyip yeniden dener (son_zaman'a kadar). Kalıcı hatada durur."""
    deneme = 0
    while True:
        try:
            return fn()
        except GraphHatasi as h:
            if not h.gecici():
                raise Dur(f"{is_adi}: {h.kisa()}")
            b = bekleme_suresi(deneme, h)
            if zaman() + b > son_zaman:
                raise Dur(f"{is_adi}: geçici hata sürdü, süre doldu ({h.kisa()})")
            uyari(f"{is_adi}: geçici hata ({h.kisa()}); {b} sn sonra yeniden")
            uyu(b)
            deneme += 1


# ---------- Kayıt etiketi (kilit 1) ----------
def etiket_adi(tarih):
    return f"paylasildi/{tarih.isoformat()}"


def etiket_var(tarih):
    r = subprocess.run(["git", "ls-remote", "--tags", "origin", f"refs/tags/{etiket_adi(tarih)}"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        uyari("Kayıt etiketi okunamadı; Instagram'daki gönderilere bakılacak (kilit 2).")
        return False
    return bool(r.stdout.strip())


def etiket_koy(tarih, mesaj):
    ad = etiket_adi(tarih)
    for i in range(3):
        a = subprocess.run(["git", "-c", "user.name=aksama-paylasim", "-c", "user.email=aksama-paylasim@users.noreply.github.com",
                            "tag", "-f", "-a", ad, "-m", mesaj], capture_output=True, text=True)
        b = subprocess.run(["git", "push", "origin", f"refs/tags/{ad}"], capture_output=True, text=True, timeout=120)
        if a.returncode == 0 and b.returncode == 0:
            return True
        uyari(f"Kayıt etiketi yazılamadı (deneme {i + 1}): {(b.stderr or a.stderr).strip()[:200]}")
        uyu(10)
    return False


# ---------- Instagram'da bugün paylaşılmış mı (kilit 2) ----------
def ilk_satir(metin):
    for s in (metin or "").splitlines():
        if s.strip():
            return " ".join(s.split())
    return ""


def bugun_paylasilmis(tarih, ilk):
    """Hesabın son gönderilerinde bugünün kaydırmalı gönderisi var mı (aynı ilk satır)? Döner: medya kimliği ya da None."""
    r = graph("GET", f"{IG_ID}/media", {"fields": "id,caption,media_type,timestamp", "limit": "10"})
    for m in r.get("data", []):
        try:
            gun = dt.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(IST).date()
        except (KeyError, ValueError):
            continue
        if gun == tarih and m.get("media_type") == "CAROUSEL_ALBUM" and ilk_satir(m.get("caption")) == ilk:
            return m["id"]
    return None


# ---------- Özel depo (aksama-bot) ----------
def gh_oku(yol, ham=True):
    url = f"{GITHUB_API}/repos/{BOT_DEPO}/contents/{urllib.parse.quote(yol)}"
    basliklar = {"Authorization": f"Bearer {BOT_OKUMA}", "X-GitHub-Api-Version": "2022-11-28",
                 "Accept": "application/vnd.github.raw+json" if ham else "application/vnd.github+json",
                 "User-Agent": "aksama-medya-paylasim"}
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=basliklar), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (401, 403):
                raise Dur(f"Özel depo okunamadı (HTTP {e.code}): BOT_OKUMA anahtarı eksik, süresi dolmuş ya da yetkisiz.")
            if e.code < 500 or i == 2:
                raise Dur(f"Özel depo okunamadı (HTTP {e.code}).")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if i == 2:
                raise Dur(f"Özel depoya ulaşılamadı: {str(e)[:120]}")
        uyu(10)


def gun_indir(tarih, hedef):
    """Günün klasörünü indirir. Döner: paylasim.json içeriği ya da None (klasör/dosya yok)."""
    p = gh_oku(f"gunler/{tarih}/paylasim.json")
    if p is None:
        return None
    paylasim = json.loads(p.decode("utf-8"))
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "paylasim.json").write_bytes(p)
    for ad in list(paylasim.get("kareler") or []) + [paylasim.get("aciklama") or "aciklama.txt"]:
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", ad) or ".." in ad:
            raise Dur("paylasim.json içinde geçersiz dosya adı")
        veri = gh_oku(f"gunler/{tarih}/{ad}")
        if veri is not None:
            (hedef / ad).parent.mkdir(parents=True, exist_ok=True)
            (hedef / ad).write_bytes(veri)
    return paylasim


def stok_say(bugun):
    """Bugün dâhil, onaylı (yalnız prova değil) gün sayısı (ilk STOK_BAKIS gün)."""
    liste = gh_oku("gunler", ham=False)
    if liste is None:
        return 0
    adlar = sorted(o["name"] for o in json.loads(liste) if o.get("type") == "dir" and TARIH_KALIBI.match(o["name"]))
    adlar = [a for a in adlar if dt.date.fromisoformat(a) >= bugun][:STOK_BAKIS]
    sayi = 0
    for a in adlar:
        p = gh_oku(f"gunler/{a}/paylasim.json")
        if p:
            onay = json.loads(p.decode("utf-8")).get("onay")
            if onay and not onay.get("yalniz_prova"):
                sayi += 1
    return sayi


# ---------- Paylaşım denetimi (aksama-bot/uretim/ortak.py ile aynı kurallar) ----------
def dosya_ozeti(yol):
    return hashlib.sha256(pathlib.Path(yol).read_bytes()).hexdigest()


def icerik_ozeti(klasor, kareler, aciklama):
    satirlar = [f"{k} {dosya_ozeti(klasor / k)}" for k in kareler]
    satirlar.append(f"{aciklama} {dosya_ozeti(klasor / aciklama)}")
    return hashlib.sha256("\n".join(satirlar).encode()).hexdigest()


def jpeg_bilgisi(yol):
    b = pathlib.Path(yol).read_bytes()
    if b[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF:
            i += 1
            continue
        if b[i + 1] in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(b[i + 2:i + 4], "big")
    return None


def etiket_sayisi(metin):
    return sum(1 for s in metin.split() if s.startswith("#") and len(s) > 1)


def gun_denetle(klasor, p, tarih, kip):
    sorun = []
    if p.get("tarih") != tarih.isoformat():
        sorun.append("paylasim.json tarihi tutmuyor")
    kareler = p.get("kareler") or []
    if not KARE_EN_AZ <= len(kareler) <= KARE_EN_COK:
        sorun.append(f"kare sayısı {len(kareler)} ({KARE_EN_AZ}-{KARE_EN_COK} olmalı)")
    for k in kareler:
        yol = klasor / k
        if not yol.is_file():
            sorun.append(f"kare yok: {k}")
            continue
        b = jpeg_bilgisi(yol)
        if not b:
            sorun.append(f"JPEG değil: {k}")
        elif b != (GEN, YUK):
            sorun.append(f"boyut {b[0]}x{b[1]}: {k}")
        if yol.stat().st_size > KARE_BOYUT_EN_COK:
            sorun.append(f"8 MB'tan büyük: {k}")
    ac = p.get("aciklama") or ""
    if not (klasor / ac).is_file():
        sorun.append("açıklama dosyası yok")
    else:
        metin = (klasor / ac).read_text(encoding="utf-8").strip()
        if not metin:
            sorun.append("açıklama boş")
        if len(metin) > ACIKLAMA_EN_COK:
            sorun.append(f"açıklama {len(metin)} harf (sınır {ACIKLAMA_EN_COK})")
        if etiket_sayisi(metin) > ETIKET_EN_COK:
            sorun.append(f"{etiket_sayisi(metin)} etiket (en çok {ETIKET_EN_COK})")
    alt = p.get("alt_metinler")
    if alt is not None and (not isinstance(alt, list) or len(alt) != len(kareler)):
        sorun.append("alt_metinler kare sayısıyla aynı uzunlukta olmalı")
    if sorun:
        return sorun
    ozet_ = icerik_ozeti(klasor, kareler, ac)
    if p.get("ozet") != ozet_:
        sorun.append("içerik özeti tutmuyor (dosyalar sonradan değişmiş)")
    onay = p.get("onay")
    if not onay:
        sorun.append("onay yok")
    elif onay.get("ozet") != ozet_:
        sorun.append("onaydan sonra içerik değişmiş")
    elif kip == "yayin" and onay.get("yalniz_prova"):
        sorun.append("bu günün onayı yalnız prova için")
    return sorun


# ---------- Adım 1: hazırla ----------
def kip_belirle():
    girdi = (os.environ.get("KIP_GIRDI") or "otomatik").strip().lower()
    ayar = (os.environ.get("KIP_AYARI") or "").strip().lower() or "kontrol"
    if ayar not in KIPLER:
        uyari(f"PAYLASIM_KIPI tanınmadı ({ayar}); kontrol sayıldı.")
        ayar = "kontrol"
    kip = ayar if girdi == "otomatik" else girdi
    if kip not in KIPLER:
        raise Dur(f"Bilinmeyen kip: {kip}")
    if kip == "yayin" and ayar != "yayin":
        uyari("Gerçek paylaşım kapalı (PAYLASIM_KIPI=yayin değil); prova yapılıyor.")
        kip = "prova"
    return kip, girdi


def anahtar_denetle():
    if not TOKEN:
        raise Dur("IG_TOKEN yok: aksama-medya → Settings → Secrets and variables → Actions → IG_TOKEN.")
    try:
        h = graph("GET", IG_ID, {"fields": "id,username"})
    except GraphHatasi as e:
        raise Dur(f"Instagram hesabı okunamadı: {e.kisa()}")
    if h.get("username") != HESAP_ADI:
        raise Dur(f"Anahtar {HESAP_ADI} hesabına bağlı değil (okunan: {h.get('username')}); paylaşım yapılmaz.")
    bilgi(f"Hesap: @{HESAP_ADI} (kilit tamam)")
    try:
        d = graph("GET", "debug_token", {"input_token": TOKEN}).get("data", {})
    except GraphHatasi as e:
        uyari(f"Anahtar bilgisi okunamadı (belirsiz): {e.kisa()}")
        return
    if d.get("is_valid") is False:
        raise Dur("Anahtar geçersiz (debug_token).")
    izin = d.get("scopes") or []
    bitis = d.get("expires_at") or 0
    erisim = d.get("data_access_expires_at") or 0
    bilgi(f"Anahtar: tür {d.get('type', 'belirsiz')}; süre {'süresiz' if not bitis else dt.datetime.fromtimestamp(bitis, IST).strftime('%d.%m.%Y %H:%M')}; "
          f"veri erişimi {'süresiz' if not erisim else dt.datetime.fromtimestamp(erisim, IST).strftime('%d.%m.%Y')}; izinler: {', '.join(izin) or 'belirsiz'}")
    if izin and "instagram_content_publish" not in izin:
        raise Dur("Anahtarda instagram_content_publish izni yok.")
    for ad, t in (("Anahtarın", bitis), ("Veri erişiminin", erisim)):
        if t and dt.datetime.fromtimestamp(t, IST) - simdi() < dt.timedelta(days=14):
            uyari(f"{ad} süresi 14 günden az kaldı; yenilenmeli.")


def pay_denetle():
    try:
        r = graph("GET", f"{IG_ID}/content_publishing_limit", {"fields": "quota_usage,config"})
    except GraphHatasi as e:
        uyari(f"Paylaşım payı okunamadı: {e.kisa()}")
        return
    d = (r.get("data") or [{}])[0]
    kullanilan, toplam = d.get("quota_usage"), (d.get("config") or {}).get("quota_total")
    bilgi(f"Instagram paylaşım payı (24 saat): {kullanilan}/{toplam}")
    if kullanilan is not None and toplam and kullanilan >= toplam:
        raise Dur("Instagram'ın 24 saatlik paylaşım payı dolu.")


def hazirla():
    kip, girdi = kip_belirle()
    an = simdi()
    bugun = an.date()
    t_girdi = (os.environ.get("TARIH_GIRDI") or "").strip()
    if t_girdi:
        if not TARIH_KALIBI.match(t_girdi):
            raise Dur("Tarih YYYY-AA-GG olmalı.")
        tarih = dt.date.fromisoformat(t_girdi)
        if kip == "yayin" and tarih != bugun:
            raise Dur("Yalnız bugünün menüsü paylaşılır; başka tarih yalnız kontrol ve prova içindir.")
    else:
        tarih = bugun
    cikti("kip", kip)
    cikti("tarih", tarih.isoformat())
    ozet(f"### Paylaşım · {tarih.isoformat()} · kip: {kip}")
    bilgi(f"Saat (İstanbul): {an.strftime('%H:%M')}")

    if girdi != "otomatik" and kip != "yayin" and YASAK[0] <= an.time() < YASAK[1]:
        raise Bitti("08:00–09:20 arasında elle kontrol ve prova yapılmaz (09:00 paylaşımı korunur).")
    if kip == "yayin":
        if an.time() < SAAT_ERKEN:
            raise Dur(f"Paylaşım {SAAT_ERKEN:%H:%M}'dan önce başlatılmaz.")
        if an.time() >= SAAT_SON:
            raise Dur(f"Saat {SAAT_SON:%H:%M}'ı geçti; bugünün menüsü paylaşılmadı. Elle bakılmalı.")
        if etiket_var(tarih):
            raise Bitti("Bugünün gönderisi zaten paylaşılmış (kayıt etiketi var).")
    elif etiket_var(tarih):
        bilgi("Not: bu tarihin kayıt etiketi var (paylaşılmış).")

    anahtar_denetle()
    pay_denetle()

    if not BOT_OKUMA:
        raise Dur("BOT_OKUMA yok: aksama-bot'u okuyacak ince anahtar (yalnız Contents: Read) bu depoya eklenmeli.")
    try:
        stok = stok_say(bugun)
        cikti("stok", stok)
        bilgi(f"Hazır stok (bugün dâhil, onaylı): {stok} gün")
        if stok < 3:
            uyari(f"Hazır stok {stok} gün; 3'ün altında.")
    except Dur as e:
        uyari(f"Stok sayılamadı: {e}")

    klasor = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "gun" / tarih.isoformat()
    shutil.rmtree(klasor, ignore_errors=True)
    p = gun_indir(tarih.isoformat(), klasor)
    if p is None:
        if kip == "kontrol":
            uyari(f"{tarih} için gün klasörü yok (gunler/{tarih}/paylasim.json).")
            ozet("Kontrol tamam: anahtar ve hesap doğru; gün klasörü yok.")
            cikti("yayina_hazir", "hayir")
            return
        raise Dur(f"{tarih} için paylaşılacak gün yok (gunler/{tarih}/paylasim.json).")
    sorun = gun_denetle(klasor, p, tarih, kip)
    if sorun:
        raise Dur("Gün denetimi geçmedi: " + "; ".join(sorun))
    aciklama = (klasor / p["aciklama"]).read_text(encoding="utf-8").strip()
    bilgi(f"Gün denetimi tamam: {len(p['kareler'])} kare, açıklama {len(aciklama)} harf, {etiket_sayisi(aciklama)} etiket, onaylı.")

    if kip == "kontrol":
        ozet("Kontrol tamam: anahtar, hesap ve gün klasörü doğru. Instagram'a ve Pages'e bir şey gönderilmedi.")
        cikti("yayina_hazir", "hayir")
        return

    # Pages: yalnız bugünün kareleri, tahmin edilemez bir klasörde (01.jpg, 02.jpg ...)
    shutil.rmtree(SITE, ignore_errors=True)
    gizli = secrets.token_hex(12)
    (SITE / gizli).mkdir(parents=True)
    (SITE / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Akşama Ne Var?</title>'
                                     '<p><a href="https://www.instagram.com/aksama.ne.var/">@aksama.ne.var</a></p>\n', encoding="utf-8")
    dosyalar = []
    for i, k in enumerate(p["kareler"], 1):
        ad = f"{i:02d}.jpg"
        shutil.copyfile(klasor / k, SITE / gizli / ad)
        dosyalar.append({"ad": ad, "boyut": (klasor / k).stat().st_size})
    DURUM.write_text(json.dumps({"tarih": tarih.isoformat(), "kip": kip, "gizli": gizli, "dosyalar": dosyalar,
                                 "aciklama": aciklama, "alt_metinler": p.get("alt_metinler")}, ensure_ascii=False), encoding="utf-8")
    cikti("yayina_hazir", "evet")


# ---------- Adım 2: yayınla ----------
def yayinda_mi(adresler, boyutlar):
    bas = zaman()
    while True:
        eksik = 0
        for a, b in zip(adresler, boyutlar):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"{a}?v={secrets.token_hex(4)}",
                                            headers={"User-Agent": "aksama-medya-paylasim"}), timeout=30) as r:
                    tamam = (r.status == 200 and r.headers.get("Content-Type", "").startswith("image/jpeg")
                             and len(r.read()) == b)
            except Exception:
                tamam = False
            eksik += not tamam
        if not eksik:
            bilgi(f"Kareler yayında ({len(adresler)}).")
            return
        if zaman() - bas > YAYINDA_SURESI:
            raise Dur(f"{eksik} kare {YAYINDA_SURESI // 60} dk içinde Pages'te görünmedi.")
        uyu(15)


def hazir_bekle(kaplar, son_zaman):
    for k in kaplar:
        for _ in range(31):
            s = dayanikli("kap durumu", lambda: graph("GET", k, {"fields": "status_code,status"}), son_zaman)
            kod = s.get("status_code")
            if kod == "FINISHED":
                break
            if kod in ("ERROR", "EXPIRED"):
                raise Dur(f"Instagram kabı {kod}: {s.get('status', '')}")
            uyu(10)
        else:
            raise Dur("Instagram kabı 5 dakikada hazır olmadı.")


def hedefi_bekle(tarih):
    hedef = dt.datetime.combine(tarih, SAAT_HEDEF, IST)
    kalan = (hedef - simdi()).total_seconds()
    if kalan > 0:
        bilgi(f"09:00 bekleniyor ({int(kalan // 60)} dk).")
    while (kalan := (hedef - simdi()).total_seconds()) > 0:
        uyu(min(kalan, 60))


def paylas_dayanikli(kap, tarih, ilk, son_zaman):
    """media_publish. Belirsiz hatada (gitmiş olabilir) Instagram'a bakmadan yeniden denemez."""
    deneme = 0
    while True:
        try:
            return graph("POST", f"{IG_ID}/media_publish", {"creation_id": kap}, zaman_asimi=120)
        except GraphHatasi as h:
            if not h.gecici():
                raise Dur(f"Paylaşılamadı: {h.kisa()}")
            uyari(f"Paylaşım: geçici hata ({h.kisa()}); gidip gitmediğine bakılacak.")
            hata = h
        while True:
            b = bekleme_suresi(deneme, hata)
            if zaman() + b > son_zaman:
                raise Dur("Paylaşım süresi doldu; paylaşılmadı ya da belirsiz. Instagram'a elle bakılmalı.")
            uyu(b)
            deneme += 1
            try:
                var = bugun_paylasilmis(tarih, ilk)
                break
            except GraphHatasi as h2:
                uyari(f"Paylaşım denetimi okunamadı: {h2.kisa()}")
        if var:
            return {"id": var, "_onceden": True}


def yayinla():
    d = json.loads(DURUM.read_text(encoding="utf-8"))
    tarih, kip = dt.date.fromisoformat(d["tarih"]), d["kip"]
    taban = (os.environ.get("SAYFA_ADRESI") or "").rstrip("/")
    if not taban:
        raise Dur("Pages adresi yok (deploy-pages çıktısı).")
    adresler = [f"{taban}/{d['gizli']}/{f['ad']}" for f in d["dosyalar"]]
    yayinda_mi(adresler, [f["boyut"] for f in d["dosyalar"]])

    son_zaman = zaman() + DENEME_SURESI
    alt = d.get("alt_metinler") or [None] * len(adresler)
    cocuklar = []
    for adres, a in zip(adresler, alt):
        prm = {"image_url": adres, "is_carousel_item": "true", "alt_text": a}
        cocuklar.append(dayanikli("kare kabı", lambda prm=prm: graph("POST", f"{IG_ID}/media", prm)["id"], son_zaman))
    hazir_bekle(cocuklar, son_zaman)
    prm = {"media_type": "CAROUSEL", "children": ",".join(cocuklar), "caption": d["aciklama"]}
    if (os.environ.get("YZ_ETIKETI") or "evet").strip().lower() != "hayir":
        prm["is_ai_generated"] = "true"
    kap = dayanikli("gönderi kabı", lambda: graph("POST", f"{IG_ID}/media", prm)["id"], son_zaman)
    hazir_bekle([kap], son_zaman)
    bilgi(f"Instagram kapları hazır: {len(cocuklar)} kare + gönderi" + (" (YZ etiketi açık)" if "is_ai_generated" in prm else ""))

    if kip == "prova":
        ozet(f"Prova tamam: {len(cocuklar)} kare Pages'ten Instagram'a yüklendi, gönderi hazır; **paylaşılmadı** "
             "(kap 24 saatte kendiliğinden silinir).")
        return

    hedefi_bekle(tarih)
    if simdi().time() >= SAAT_SON:
        raise Dur(f"Saat {SAAT_SON:%H:%M}'ı geçti; paylaşılmadı.")
    if etiket_var(tarih):
        raise Bitti("Bugünün gönderisi zaten paylaşılmış (kayıt etiketi var).")
    ilk = ilk_satir(d["aciklama"])
    var = dayanikli("paylaşım denetimi", lambda: bugun_paylasilmis(tarih, ilk), son_zaman)
    if var:
        etiket_koy(tarih, f"media {var} (Instagram'da önceden paylaşılmış bulundu)")
        raise Bitti("Bugünün gönderisi Instagram'da zaten var; yeniden paylaşılmadı.")

    sonuc = paylas_dayanikli(kap, tarih, ilk, son_zaman)
    mid = sonuc["id"]
    sorun = sonuc.get("config_issue")
    try:
        m = graph("GET", mid, {"fields": "permalink,timestamp"})
    except GraphHatasi:
        m = {}
    yazildi = etiket_koy(tarih, f"media {mid} {m.get('permalink', '')} {m.get('timestamp', '')}".strip())
    ozet(f"**Paylaşıldı** {simdi():%H:%M}: {m.get('permalink', mid)}" + (" (önceki denemede gitmiş)" if sonuc.get("_onceden") else ""))
    if sorun:
        raise Dur(f"Paylaşıldı ama Instagram bir kısmını düşürdü: {sorun}. Gönderiye elle bakılmalı.")
    if not yazildi:
        raise Dur("Paylaşıldı ama kayıt etiketi yazılamadı (nöbetçi yanlış uyarı verebilir).")


def main():
    adim = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if adim == "hazirla":
            hazirla()
        elif adim == "yayinla":
            yayinla()
        else:
            sys.exit("kullanım: paylas.py hazirla|yayinla")
    except Bitti as e:
        cikti("yayina_hazir", "hayir")
        ozet(f"Yapılacak iş yok: {e}")
    except Dur as e:
        cikti("yayina_hazir", "hayir")
        print(f"::error::{e}", flush=True)
        ozet(f"**Durdu:** {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
