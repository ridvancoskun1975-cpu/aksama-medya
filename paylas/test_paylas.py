"""Paylaşım işinin denemesi: sahte Instagram, sahte GitHub ve sahte Pages ile, sahte saatle.
Gerçek hesaba ve gerçek depoya hiçbir şey gönderilmez. Pillow gerekir (deneme kareleri için).
Çalıştırma: python3 paylas/test_paylas.py -v
"""
import datetime as dt
import hashlib
import http.server
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse
from contextlib import redirect_stdout

GECICI = pathlib.Path(tempfile.mkdtemp(prefix="aksama-deneme-"))
SUNUCU = {}


class Sahte:
    def __init__(self):
        self.kullanici = "aksama.ne.var"
        self.kap_sayac = 0
        self.kaplar = {}            # id -> parametreler
        self.medya = []             # yayımlananlar
        self.istekler = []          # (yöntem, yol, parametreler)
        self.davranis = {}          # "publish" / "carousel" / "kare" -> [davranış, ...]
        self.kap_durumu = {}        # kap -> status_code (varsayılan FINISHED)
        self.saat = None
        self.yuklemeler = []        # (kap, bayt) kapak videosu yüklemeleri
        self.anahtar = {"type": "SYSTEM_USER", "is_valid": True, "expires_at": 0, "data_access_expires_at": 0,
                        "scopes": ["instagram_basic", "instagram_content_publish"]}     # debug_token cevabı
        self.gunler = GECICI / "gunler"
        self.site = GECICI / "_site"

    def sonraki(self, ad):
        liste = self.davranis.get(ad) or []
        return liste.pop(0) if liste else None

    def yayinlar(self):
        return [i for i in self.istekler if i[0] == "POST" and i[1].endswith("/media_publish")]

    def ig_yazmalari(self):
        return [i for i in self.istekler if i[0] == "POST"]


S = Sahte()


class Isleyici(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def cevap(self, kod, govde, tur="application/json"):
        veri = govde if isinstance(govde, bytes) else json.dumps(govde).encode()
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def hata(self, kod, ig_kod, alt=None, gecici=False, mesaj="hata"):
        self.cevap(kod, {"error": {"code": ig_kod, "error_subcode": alt, "is_transient": gecici, "message": mesaj}})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path.startswith("/pages/"):
            yol = S.site / u.path[len("/pages/"):]
            return self.cevap(200, yol.read_bytes(), "image/jpeg") if yol.is_file() else self.cevap(404, b"", "text/html")
        if u.path.startswith("/gh/repos/ridvancoskun1975-cpu/aksama-bot/contents/"):
            if self.headers.get("Authorization") != "Bearer bot-anahtar":
                return self.cevap(401, {"message": "Bad credentials"})
            yol = S.gunler.parent / urllib.parse.unquote(u.path.split("/contents/", 1)[1])
            if yol.is_dir():
                return self.cevap(200, [{"name": c.name, "type": "dir" if c.is_dir() else "file"} for c in yol.iterdir()])
            return self.cevap(200, yol.read_bytes(), "application/octet-stream") if yol.is_file() else self.cevap(404, {"message": "Not Found"})
        if not u.path.startswith("/graph/"):
            return self.cevap(404, {})
        if self.headers.get("Authorization") != "Bearer ig-anahtar":
            return self.hata(400, 190, mesaj="Invalid OAuth access token")
        yol = u.path[len("/graph/"):]
        S.istekler.append(("GET", yol, q))
        if yol == "17841474308613858":
            return self.cevap(200, {"id": yol, "username": S.kullanici})
        if yol == "debug_token":
            return self.cevap(200, {"data": dict(S.anahtar)})
        if yol.endswith("/content_publishing_limit"):
            return self.cevap(200, {"data": [{"quota_usage": 0, "config": {"quota_total": 100}}]})
        if yol.endswith("/media"):
            return self.cevap(200, {"data": list(reversed(S.medya))[:int(q.get("limit", 25))]})
        if yol in S.kaplar:
            return self.cevap(200, {"status_code": S.kap_durumu.get(yol, "FINISHED"), "status": "durum"})
        for m in S.medya:
            if m["id"] == yol:
                return self.cevap(200, {"permalink": f"https://www.instagram.com/p/{yol}/", "timestamp": m["timestamp"]})
        return self.hata(400, 100, mesaj="Unsupported get request")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        uzunluk = int(self.headers.get("Content-Length") or 0)
        if u.path.startswith("/rupload/"):
            # Kapak videosu doğrudan yükleme (rupload.facebook.com yerine)
            govde = self.rfile.read(uzunluk)
            if self.headers.get("Authorization") != "OAuth ig-anahtar":
                return self.hata(400, 190, mesaj="Invalid OAuth access token")
            d = S.sonraki("rupload")
            if d == "100":
                return self.hata(400, 100, mesaj="Invalid upload")
            if d == "500":
                return self.hata(500, 2, gecici=True)
            S.yuklemeler.append((u.path.rsplit("/", 1)[-1], len(govde), self.headers.get("file_size")))
            return self.cevap(200, {"success": True})
        q = dict(urllib.parse.parse_qsl(self.rfile.read(uzunluk).decode()))
        yol = u.path[len("/graph/"):]
        if self.headers.get("Authorization") != "Bearer ig-anahtar":
            return self.hata(400, 190, mesaj="Invalid OAuth access token")
        S.istekler.append(("POST", yol, q))
        if yol.endswith("/media"):
            ad = {"CAROUSEL": "carousel", "VIDEO": "video"}.get(q.get("media_type"), "kare")
            d = S.sonraki(ad)
            if d == "100":
                return self.hata(400, 100, mesaj="Invalid parameter")
            if d == "500":
                return self.hata(500, 2, gecici=True, mesaj="Service temporarily unavailable")
            if ad == "carousel":
                # Kaydırmalıdaki video kare yüklenmeden kullanılamaz
                for c in q["children"].split(","):
                    if S.kaplar.get(c, {}).get("media_type") == "VIDEO" and c not in [y[0] for y in S.yuklemeler]:
                        return self.hata(400, 9007, 2207027, mesaj="Media not ready")
            if ad == "kare":
                # Instagram görseli adresten çeker: adres gerçekten açılıyor mu?
                yerel = q["image_url"].split("/pages/", 1)[1]
                if not (S.site / yerel).is_file():
                    return self.hata(400, 9004, 2207052, mesaj="Media download failed")
            S.kap_sayac += 1
            kid = f"kap{S.kap_sayac}"
            S.kaplar[kid] = q
            if ad == "video":
                if d in ("ERROR", "IN_PROGRESS"):
                    S.kap_durumu[kid] = d
                return self.cevap(200, {"id": kid, "uri": f"https://baska.example/ig-api-upload/v26.0/{kid}"})
            return self.cevap(200, {"id": kid})
        if yol.endswith("/media_publish"):
            d = S.sonraki("publish")
            if d == "500":
                return self.hata(500, 2, gecici=True)
            if d == "100":
                return self.hata(400, 100, mesaj="Invalid parameter")
            kap = S.kaplar[q["creation_id"]]
            mid = f"medya{len(S.medya) + 1}"
            S.medya.append({"id": mid, "caption": kap.get("caption"), "media_type": "CAROUSEL_ALBUM",
                            "timestamp": S.saat.t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")})
            if d == "500_gitti":
                return self.hata(500, 2, gecici=True)
            if d == "config":
                return self.cevap(200, {"id": mid, "config_issue": "CAPTION_NOT_ATTACHED"})
            return self.cevap(200, {"id": mid})
        return self.hata(400, 100)


def sunucuyu_baslat():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


ADRES = sunucuyu_baslat()
os.environ.update({"GRAPH_ADRESI": f"{ADRES}/graph", "GITHUB_API_URL": f"{ADRES}/gh", "IG_TOKEN": "ig-anahtar",
                   "RUPLOAD_ADRESI": f"{ADRES}/rupload",
                   "BOT_OKUMA": "bot-anahtar", "RUNNER_TEMP": str(GECICI / "runner"), "SITE_KLASORU": str(S.site)})
(GECICI / "runner").mkdir()
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas  # noqa: E402

IST = paylas.IST
BUGUN = dt.date(2026, 11, 20)
ACIKLAMA = ("Bugün ne pişireyim? DENEME menüsü: çorba, ana yemek, yan yemek, tatlı.\n\nGİZLİ-MENÜ-METNİ\n\n"
            "Görseller temsilidir, yapay zekâ ile hazırlanmıştır.\n"
            "Bu içerik Akşama Ne Var?™ sayfasına aittir. İzinsiz kopyalanamaz, başka sayfada yayımlanamaz.\n\n"
            "#akşamanevar #bugünnepişireyim\n")


class Saat:
    def __init__(self, t):
        self.t = t
        self.mono = 1000.0

    def uyu(self, sn):
        self.t += dt.timedelta(seconds=sn)
        self.mono += sn


def jpeg(yol, renk):
    from PIL import Image
    Image.new("RGB", (1080, 1350), renk).save(yol, "JPEG", quality=80)


def gun_kur(tarih, onay=True, yalniz_prova=False, kare=8, aciklama=ACIKLAMA, alt=None):
    k = S.gunler / tarih.isoformat()
    shutil.rmtree(k, ignore_errors=True)
    (k / "kareler").mkdir(parents=True)
    adlar = []
    for i in range(kare):
        ad = f"kareler/{i + 1:02d}-kare.jpg"
        jpeg(k / ad, (200, 100 + i * 10, 80))
        adlar.append(ad)
    (k / "aciklama.txt").write_text(aciklama, encoding="utf-8")
    oz = paylas.icerik_ozeti(k, adlar, "aciklama.txt")
    p = {"surum": 1, "tarih": tarih.isoformat(), "kareler": adlar, "aciklama": "aciklama.txt", "ozet": oz, "alt_metinler": alt,
         "onay": ({"soz": "DENEME", "ozet": oz, **({"yalniz_prova": True} if yalniz_prova else {})} if onay else None)}
    (k / "paylasim.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    return k


class PaylasimDenemesi(unittest.TestCase):
    def setUp(self):
        global S
        S.__init__()
        shutil.rmtree(S.gunler, ignore_errors=True)
        S.gunler.mkdir(parents=True)
        for i in range(4):
            gun_kur(BUGUN + dt.timedelta(days=i))
        self.etiketler = set()
        self.kap_kayit = {}
        os.environ.pop("KAPAK_VIDEO", None)
        paylas.KAPAK_VIDEOSU = True
        paylas.etiket_var = lambda t: paylas.etiket_adi(t) in self.etiketler
        paylas.etiket_koy = lambda t, m: self.etiketler.add(paylas.etiket_adi(t)) or True
        paylas.kap_oku = lambda t: self.kap_kayit.get(t.isoformat())
        paylas.kap_yaz = lambda t, k: self.kap_kayit.__setitem__(t.isoformat(), k) or True

    def calistir(self, saat="08:20", girdi="otomatik", ayar="yayin", tarih="", yz="", asama="sabah", gun=BUGUN):
        h, m = map(int, saat.split(":"))
        S.saat = Saat(dt.datetime.combine(gun, dt.time(h, m), IST))
        paylas.simdi = lambda: S.saat.t
        paylas.zaman = lambda: S.saat.mono
        paylas.uyu = S.saat.uyu
        cikti = GECICI / "runner" / "cikti.txt"
        cikti.write_text("")
        os.environ.update({"KIP_GIRDI": girdi, "KIP_AYARI": ayar, "TARIH_GIRDI": tarih, "YZ_ETIKETI": yz, "ASAMA": asama,
                           "GITHUB_OUTPUT": str(cikti), "SAYFA_ADRESI": f"{ADRES}/pages/"})
        gunluk = io.StringIO()
        sonuc = "tamam"
        with redirect_stdout(gunluk):
            try:
                paylas.hazirla()
                ciktilar = dict(s.split("=", 1) for s in cikti.read_text().splitlines() if "=" in s)
                if ciktilar.get("yayina_hazir") == "evet":
                    paylas.yayinla()
            except paylas.Dur as e:
                sonuc = f"dur: {e}"
            except paylas.Bitti as e:
                sonuc = f"bitti: {e}"
        self.gunluk = gunluk.getvalue()
        self.ciktilar = dict(s.split("=", 1) for s in cikti.read_text().splitlines() if "=" in s)
        self.assertNotIn("GİZLİ-MENÜ-METNİ", self.gunluk, "açıklama metni açık günlüğe yazılmamalı")
        self.assertNotIn("ig-anahtar", self.gunluk)
        self.assertNotIn("bot-anahtar", self.gunluk)
        return sonuc

    # --- kipler ---
    def test_kontrol_instagrama_yazmaz(self):
        r = self.calistir(saat="20:00", ayar="kontrol")
        self.assertEqual(r, "tamam")
        self.assertEqual(S.ig_yazmalari(), [])
        self.assertEqual(self.ciktilar["yayina_hazir"], "hayir")
        self.assertEqual(self.ciktilar["stok"], "4")

    def test_ayar_bossa_kontrol(self):
        self.assertEqual(self.calistir(saat="20:00", ayar=""), "tamam")
        self.assertEqual(self.ciktilar["kip"], "kontrol")
        self.assertEqual(S.ig_yazmalari(), [])

    def test_prova_paylasmaz(self):
        r = self.calistir(saat="20:00", ayar="prova")
        self.assertEqual(r, "tamam")
        self.assertEqual(S.yayinlar(), [])
        kaplar = [i for i in S.ig_yazmalari() if i[1].endswith("/media")]
        self.assertEqual(len(kaplar), 9)
        self.assertEqual(kaplar[-1][2]["caption"], ACIKLAMA.strip())
        self.assertNotIn("is_ai_generated", kaplar[-1][2])        # Meta etiketi varsayılan kapalı
        self.assertEqual(len(kaplar[-1][2]["children"].split(",")), 8)

    def test_alt_metin_karelere_gider(self):
        gun_kur(BUGUN, alt=[f"alt {i}" for i in range(8)])
        self.calistir(saat="20:00", ayar="prova")
        kareler = [i[2] for i in S.ig_yazmalari() if i[2].get("is_carousel_item")]
        self.assertEqual([k["alt_text"] for k in kareler], [f"alt {i}" for i in range(8)])
        gun_kur(BUGUN, alt=["eksik"])
        self.assertIn("alt_metinler", self.calistir(saat="20:00", ayar="prova"))

    def test_yz_etiketi_acilabilir(self):
        self.calistir(saat="20:00", ayar="prova", yz="evet")
        self.assertEqual(S.ig_yazmalari()[-1][2]["is_ai_generated"], "true")

    def test_yz_satiri_yoksa_paylasmaz(self):
        gun_kur(BUGUN, aciklama="Bugün ne pişireyim? Menü.\n\n#akşamanevar\n")
        self.assertIn("YZ satırı yok", self.calistir(saat="08:20"))
        self.assertEqual(S.ig_yazmalari(), [])

    def test_telif_satiri_yoksa_paylasmaz(self):
        gun_kur(BUGUN, aciklama="Bugün ne pişirsem? Menü.\n\nGörseller temsilidir, yapay zekâ ile hazırlanmıştır.\n\n#akşamanevar\n")
        self.assertIn("telif satırı yok", self.calistir(saat="08:20"))
        self.assertEqual(S.ig_yazmalari(), [])

    def test_yayin_ayar_kapaliysa_provaya_duser(self):
        r = self.calistir(saat="20:00", girdi="yayin", ayar="prova")
        self.assertEqual(r, "tamam")
        self.assertEqual(self.ciktilar["kip"], "prova")
        self.assertEqual(S.yayinlar(), [])

    def test_yayin_0900_bekler_ve_bir_kez_paylasir(self):
        r = self.calistir(saat="08:20")
        self.assertEqual(r, "tamam")
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertEqual(S.medya[0]["timestamp"][11:16], "06:00")   # 09:00 İstanbul = 06:00 UTC
        self.assertIn("paylasildi/2026-11-20", self.etiketler)
        self.assertEqual(self.calistir(saat="08:30")[:5], "bitti")  # ikinci tetik: kilit 1
        self.assertEqual(len(S.yayinlar()), 1)

    def test_gec_baslarsa_hemen_paylasir(self):
        self.assertEqual(self.calistir(saat="09:40"), "tamam")
        self.assertEqual(S.medya[0]["timestamp"][11:16], "06:40")

    def test_kilit2_instagramda_varsa_paylasmaz(self):
        S.saat = Saat(dt.datetime.combine(BUGUN, dt.time(7, 0), IST))
        S.medya.append({"id": "eski", "caption": ACIKLAMA.strip(), "media_type": "CAROUSEL_ALBUM",
                        "timestamp": "2026-11-20T05:59:00+0000"})
        r = self.calistir(saat="08:20")
        self.assertEqual(r[:5], "bitti")
        self.assertEqual(S.yayinlar(), [])
        self.assertIn("paylasildi/2026-11-20", self.etiketler)

    def test_dunku_gonderi_kilidi_tetiklemez(self):
        S.medya.append({"id": "dun", "caption": ACIKLAMA.strip(), "media_type": "CAROUSEL_ALBUM",
                        "timestamp": "2026-11-19T06:00:00+0000"})
        self.assertEqual(self.calistir(saat="08:20"), "tamam")
        self.assertEqual(len(S.yayinlar()), 1)

    def test_belirsiz_hatada_ikinci_kez_paylasmaz(self):
        S.davranis["publish"] = ["500_gitti"]
        r = self.calistir(saat="08:20")
        self.assertEqual(r, "tamam")
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertEqual(len(S.medya), 1)
        self.assertIn("paylasildi/2026-11-20", self.etiketler)

    def test_gecici_hatada_yeniden_dener(self):
        S.davranis["publish"] = ["500", "500"]
        S.davranis["kare"] = ["500"]
        self.assertEqual(self.calistir(saat="08:20"), "tamam")
        self.assertEqual(len(S.yayinlar()), 3)
        self.assertEqual(len(S.medya), 1)

    def test_kalici_hatada_durur(self):
        S.davranis["carousel"] = ["100"]
        r = self.calistir(saat="08:20")
        self.assertTrue(r.startswith("dur: gönderi kabı"))
        self.assertEqual(S.yayinlar(), [])

    def test_aciklama_dusurulurse_kirmizi(self):
        S.davranis["publish"] = ["config"]
        r = self.calistir(saat="08:20")
        self.assertIn("CAPTION_NOT_ATTACHED", r)
        self.assertIn("paylasildi/2026-11-20", self.etiketler)

    # --- hesap ve anahtar ---
    def test_baska_hesap_kilidi(self):
        S.kullanici = "gunluk.gumus"
        r = self.calistir(saat="08:20")
        self.assertIn("bağlı değil", r)
        self.assertEqual(S.ig_yazmalari(), [])

    def test_anahtar_yoksa_durur(self):
        eski, paylas.TOKEN = paylas.TOKEN, ""
        try:
            self.assertIn("IG_TOKEN yok", self.calistir(saat="20:00", ayar="kontrol"))
        finally:
            paylas.TOKEN = eski

    def test_bot_anahtari_yanlissa_durur(self):
        eski, paylas.BOT_OKUMA = paylas.BOT_OKUMA, "yanlis"
        try:
            r = self.calistir(saat="08:20")
            self.assertIn("BOT_OKUMA", r)
            self.assertEqual(S.ig_yazmalari(), [])
        finally:
            paylas.BOT_OKUMA = eski

    # --- gün denetimi ---
    def test_onaysiz_gun_paylasilmaz(self):
        gun_kur(BUGUN, onay=False)
        self.assertIn("onay yok", self.calistir(saat="08:20"))
        self.assertEqual(S.ig_yazmalari(), [])

    def test_onaydan_sonra_degisen_gun_paylasilmaz(self):
        k = gun_kur(BUGUN)
        with open(k / "aciklama.txt", "a", encoding="utf-8") as f:
            f.write("sonradan eklendi\n")
        self.assertIn("özeti tutmuyor", self.calistir(saat="08:20"))
        self.assertEqual(S.ig_yazmalari(), [])

    def test_prova_onayi_yayinda_gecmez(self):
        gun_kur(BUGUN, yalniz_prova=True)
        self.assertIn("yalnız prova", self.calistir(saat="08:20"))
        self.assertEqual(S.ig_yazmalari(), [])
        self.assertEqual(self.calistir(saat="20:00", ayar="prova"), "tamam")
        self.assertEqual(S.yayinlar(), [])

    def test_fazla_etiket_ve_kare(self):
        gun_kur(BUGUN, aciklama="a Görseller temsilidir, yapay zekâ ile hazırlanmıştır. #1 #2 #3 #4 #5 #6\n")
        self.assertIn("6 etiket", self.calistir(saat="20:00", ayar="kontrol"))
        gun_kur(BUGUN, kare=11)
        self.assertIn("kare sayısı 11", self.calistir(saat="20:00", ayar="kontrol"))

    def test_gun_yoksa(self):
        shutil.rmtree(S.gunler / BUGUN.isoformat())
        self.assertEqual(self.calistir(saat="20:00", ayar="kontrol"), "tamam")
        self.assertIn("gün klasörü yok", self.gunluk)
        self.assertIn("paylaşılacak gün yok", self.calistir(saat="08:20"))

    def test_stok(self):
        for i in range(2, 4):
            shutil.rmtree(S.gunler / (BUGUN + dt.timedelta(days=i)).isoformat())
        gun_kur(BUGUN - dt.timedelta(days=1))          # geçmiş gün sayılmaz
        gun_kur(BUGUN + dt.timedelta(days=1), yalniz_prova=True)   # prova onayı sayılmaz
        self.calistir(saat="20:00", ayar="kontrol")
        self.assertEqual(self.ciktilar["stok"], "1")

    # --- saat korumaları ---
    def test_gec_saatte_de_paylasir(self):
        self.assertEqual(self.calistir(saat="16:05"), "tamam")
        self.assertEqual(len(S.yayinlar()), 1)

    def test_23ten_sonra_paylasmaz(self):
        self.assertIn("23:00", self.calistir(saat="23:05"))
        self.assertEqual(S.ig_yazmalari(), [])

    # --- akşam hazırlığı ---
    def kap_yuklemeleri(self):
        return [i for i in S.ig_yazmalari() if i[1].endswith("/media")]

    def test_aksam_hazirlar_paylasmaz(self):
        self.assertEqual(self.calistir(saat="20:00", asama="aksam"), "tamam")
        self.assertEqual(self.ciktilar["tarih"], "2026-11-21")
        self.assertEqual(len(self.kap_yuklemeleri()), 9)
        self.assertEqual(S.yayinlar(), [])
        self.assertIn("2026-11-21", self.kap_kayit)

    def test_aksam_sonra_sabah_yalniz_paylasir(self):
        self.calistir(saat="20:00", asama="aksam")
        S.istekler.clear()
        yarin = BUGUN + dt.timedelta(days=1)
        self.assertEqual(self.calistir(saat="08:20", gun=yarin), "tamam")
        self.assertEqual(self.ciktilar.get("pages_gerek"), "hayir")
        self.assertEqual(self.kap_yuklemeleri(), [])          # kareler yeniden yüklenmedi
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertEqual(S.medya[0]["timestamp"][11:16], "06:00")
        self.assertIn("paylasildi/2026-11-21", self.etiketler)

    def test_aksamdan_sonra_icerik_degisirse_yeniden_hazirlar(self):
        self.calistir(saat="20:00", asama="aksam")
        yarin = BUGUN + dt.timedelta(days=1)
        gun_kur(yarin, aciklama=ACIKLAMA + "düzeltme\n")
        S.istekler.clear()
        self.assertEqual(self.calistir(saat="08:20", gun=yarin), "tamam")
        self.assertEqual(len(self.kap_yuklemeleri()), 9)
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertIn("düzeltme", S.medya[0]["caption"])

    def test_kap_gecersizse_yeniden_hazirlar(self):
        self.calistir(saat="20:00", asama="aksam")
        S.kap_durumu[self.kap_kayit["2026-11-21"]["kap"]] = "EXPIRED"
        S.istekler.clear()
        self.assertEqual(self.calistir(saat="08:20", gun=BUGUN + dt.timedelta(days=1)), "tamam")
        self.assertEqual(len(self.kap_yuklemeleri()), 9)
        self.assertEqual(len(S.yayinlar()), 1)

    def test_aksam_kontrol_kipinde_yazmaz(self):
        self.assertEqual(self.calistir(saat="20:00", asama="aksam", ayar="kontrol"), "tamam")
        self.assertEqual(S.ig_yazmalari(), [])
        self.assertEqual(self.kap_kayit, {})

    def test_aksam_gun_yoksa_kirmizi(self):
        shutil.rmtree(S.gunler / (BUGUN + dt.timedelta(days=1)).isoformat())
        self.assertIn("paylaşılacak gün yok", self.calistir(saat="20:00", asama="aksam"))

    def test_aksam_prova_onayli_gun_yayinda_kirmizi(self):
        gun_kur(BUGUN + dt.timedelta(days=1), yalniz_prova=True)
        self.assertIn("yalnız prova", self.calistir(saat="20:00", asama="aksam"))
        self.assertEqual(S.ig_yazmalari(), [])

    def test_aksam_paylasilmis_gunu_hazirlamaz(self):
        self.etiketler.add("paylasildi/2026-11-21")
        self.assertEqual(self.calistir(saat="20:00", asama="aksam")[:5], "bitti")
        self.assertEqual(S.ig_yazmalari(), [])

    def test_sabah_basarisizsa_gun_ici_deneme_ayni_kabi_kullanir(self):
        S.davranis["publish"] = ["100"]
        self.assertIn("Paylaşılamadı", self.calistir(saat="08:20"))
        self.assertEqual(S.medya, [])
        S.istekler.clear()
        self.assertEqual(self.calistir(saat="11:40"), "tamam")   # 11:40 yedek saati
        self.assertEqual(self.kap_yuklemeleri(), [])
        self.assertEqual(len(S.medya), 1)

    def test_prova_aksam_ve_sabah_paylasmaz(self):
        self.calistir(saat="20:00", asama="aksam", ayar="prova")
        self.assertEqual(self.calistir(saat="08:15", ayar="prova", gun=BUGUN + dt.timedelta(days=1)), "tamam")
        self.assertEqual(S.yayinlar(), [])

    def test_erken_yayin_baslamaz(self):
        self.assertIn("07:30", self.calistir(saat="06:00"))

    def test_elle_prova_0900_penceresinde_yapilmaz(self):
        self.assertEqual(self.calistir(saat="08:30", girdi="prova")[:5], "bitti")
        self.assertEqual(S.ig_yazmalari(), [])

    def test_otomatik_prova_0815te_calisir(self):
        self.assertEqual(self.calistir(saat="08:15", ayar="prova"), "tamam")

    def test_yayin_baska_tarih_olmaz(self):
        self.assertIn("Yalnız bugünün", self.calistir(saat="08:20", girdi="yayin", tarih="2026-11-21"))

    def test_baska_tarih_prova(self):
        self.assertEqual(self.calistir(saat="20:00", girdi="prova", tarih="2026-11-21"), "tamam")
        self.assertEqual(self.ciktilar["tarih"], "2026-11-21")

    # --- kapak videosu (Rıdvan 18 Kas 11:48, 12:54) ---
    def video_kur(self, tarih=BUGUN, ozet=None, uygun=True, bayt=4096):
        v = GECICI / "runner" / "kapak" / "kapak.mp4"
        v.parent.mkdir(parents=True, exist_ok=True)
        v.write_bytes(b"\x00" * bayt)
        oz = ozet or json.loads((S.gunler / tarih.isoformat() / "paylasim.json").read_text(encoding="utf-8"))["ozet"]
        v.with_suffix(".json").write_text(json.dumps({"uygun": uygun, "ozet": oz, "psnr": 45.4, "muzik": "Cotton Sky"}),
                                          encoding="utf-8")
        os.environ["KAPAK_VIDEO"] = str(v)
        return v

    def kaydirmali(self):
        return [i[2] for i in S.ig_yazmalari() if i[1].endswith("/media") and i[2].get("media_type") == "CAROUSEL"][-1]

    def test_kapak_videosu_ilk_kare_olur(self):
        self.video_kur(bayt=5000)
        self.assertEqual(self.calistir(saat="20:00", ayar="prova"), "tamam")
        cocuklar = self.kaydirmali()["children"].split(",")
        self.assertEqual(len(cocuklar), 8)                                   # video + 7 resim
        self.assertEqual(S.kaplar[cocuklar[0]]["media_type"], "VIDEO")
        self.assertEqual(S.kaplar[cocuklar[0]]["upload_type"], "resumable")
        self.assertTrue(all("image_url" in S.kaplar[c] for c in cocuklar[1:]))
        self.assertTrue(all(not S.kaplar[c]["image_url"].endswith("/01.jpg") for c in cocuklar[1:]))
        self.assertEqual(S.yuklemeler, [(cocuklar[0], 5000, "5000")])        # doğrudan yükleme, tek kez
        self.assertTrue(self.kap_kayit[BUGUN.isoformat()]["video"])
        self.assertIn("müzikli video", self.gunluk)

    def test_kapak_videosu_alt_metinleri_kaydirir(self):
        gun_kur(BUGUN, alt=[f"alt {i}" for i in range(8)])
        self.video_kur()
        self.calistir(saat="20:00", ayar="prova")
        resimler = [i[2] for i in S.ig_yazmalari() if i[2].get("is_carousel_item") and "image_url" in i[2]]
        self.assertEqual([k["alt_text"] for k in resimler], [f"alt {i}" for i in range(1, 8)])

    def test_kapak_videosu_yuklenemezse_resimli(self):
        self.video_kur()
        S.davranis["rupload"] = ["100"]
        self.assertEqual(self.calistir(saat="20:00", ayar="prova"), "tamam")
        cocuklar = self.kaydirmali()["children"].split(",")
        self.assertEqual(len(cocuklar), 8)
        self.assertTrue(all("image_url" in S.kaplar[c] for c in cocuklar))
        self.assertFalse(self.kap_kayit[BUGUN.isoformat()]["video"])
        self.assertIn("resimli kapak", self.gunluk)

    def test_kapak_videosu_gecici_hatada_yeniden_yukler(self):
        self.video_kur()
        S.davranis["rupload"] = ["500"]
        self.calistir(saat="20:00", ayar="prova")
        cocuklar = self.kaydirmali()["children"].split(",")
        self.assertEqual(S.kaplar[cocuklar[0]]["media_type"], "VIDEO")
        self.assertEqual(len(S.yuklemeler), 1)

    def test_kapak_videosu_islenmezse_resimli(self):
        self.video_kur()
        S.davranis["video"] = ["ERROR"]
        self.assertEqual(self.calistir(saat="20:00", ayar="prova"), "tamam")
        cocuklar = self.kaydirmali()["children"].split(",")
        self.assertTrue(all("image_url" in S.kaplar[c] for c in cocuklar))
        self.assertEqual(len(cocuklar), 8)

    def test_kapak_videosu_bitmezse_suresinde_birakir(self):
        self.video_kur()
        S.davranis["video"] = ["IN_PROGRESS"]
        bas = None
        self.assertEqual(self.calistir(saat="20:00", ayar="prova"), "tamam")
        self.assertTrue(all("image_url" in S.kaplar[c] for c in self.kaydirmali()["children"].split(",")))
        self.assertLessEqual(S.saat.mono - 1000.0, paylas.VIDEO_SURESI + 120)

    def test_baska_gunun_videosu_kullanilmaz(self):
        self.video_kur(ozet="baska")
        self.calistir(saat="20:00", ayar="prova")
        self.assertFalse(any(i[2].get("media_type") == "VIDEO" for i in S.ig_yazmalari()))
        self.assertEqual(S.yuklemeler, [])

    def test_uygun_olmayan_video_kullanilmaz(self):
        self.video_kur(uygun=False)
        self.calistir(saat="20:00", ayar="prova")
        self.assertFalse(any(i[2].get("media_type") == "VIDEO" for i in S.ig_yazmalari()))

    def test_video_yoksa_resimli(self):
        os.environ["KAPAK_VIDEO"] = str(GECICI / "runner" / "yok" / "kapak.mp4")
        self.assertEqual(self.calistir(saat="20:00", ayar="prova"), "tamam")
        self.assertEqual(len(self.kaydirmali()["children"].split(",")), 8)
        self.assertIn("üretilmemiş", self.gunluk)

    def test_kapatma_anahtari(self):
        self.video_kur()
        paylas.KAPAK_VIDEOSU = False
        self.calistir(saat="20:00", ayar="prova")
        self.assertFalse(any(i[2].get("media_type") == "VIDEO" for i in S.ig_yazmalari()))

    def test_aksam_videolu_sabah_ayni_kabi_paylasir(self):
        self.video_kur(tarih=BUGUN + dt.timedelta(days=1))
        self.calistir(saat="20:00", asama="aksam")
        self.assertTrue(self.kap_kayit[(BUGUN + dt.timedelta(days=1)).isoformat()]["video"])
        os.environ.pop("KAPAK_VIDEO")
        yazma = len(S.ig_yazmalari())
        self.assertEqual(self.calistir(saat="08:15", gun=BUGUN + dt.timedelta(days=1)), "tamam")
        yeni = S.ig_yazmalari()[yazma:]
        self.assertEqual([i[1].rsplit("/", 1)[-1] for i in yeni], ["media_publish"])   # yalnız paylaşım
        self.assertIn("müzikli video", self.gunluk)

    # --- otomatiğe dönüş: uzun aradan sonra (DONUS.md; yalnız sahte sunucu) ---
    def elle_gonderi(self, gun, saat, ilk_satir=None, tur="CAROUSEL_ALBUM"):
        """Rıdvan'ın telefondan elle paylaştığı gönderi: Instagram'da var, kayıt etiketi yok."""
        h, m = map(int, saat.split(":"))
        an = dt.datetime.combine(gun, dt.time(h, m), IST).astimezone(dt.timezone.utc)
        metin = ACIKLAMA.strip() if ilk_satir is None else ilk_satir + "\n" + ACIKLAMA.split("\n", 1)[1].strip()
        S.medya.append({"id": f"elle-{gun.isoformat()}", "caption": metin, "media_type": tur,
                        "timestamp": an.strftime("%Y-%m-%dT%H:%M:%S+0000")})

    def yalniz_yayin(self, yazma):
        return [i[1].rsplit("/", 1)[-1] for i in S.ig_yazmalari()[yazma:]]

    def test_donus_uzun_aradan_sonra_yalniz_bugun(self):
        # Soru 1: 21 Kas'tan beri etiketsiz (otomatik paylaşılmamış) günler bekliyor; iş yalnız bugünü paylaşır,
        # yedek saatler ve nöbetçi de eski günlere geçmez.
        donus = dt.date(2026, 12, 10)
        for i in range(1, 20):
            gun_kur(donus - dt.timedelta(days=i), aciklama="ESKİ GÜN\n" + ACIKLAMA)
        gun_kur(donus)
        self.assertEqual(self.calistir(saat="08:20", gun=donus), "tamam")
        self.assertEqual(self.ciktilar["tarih"], donus.isoformat())
        self.assertEqual([m["caption"] for m in S.medya], [ACIKLAMA.strip()])
        self.assertEqual(self.etiketler, {f"paylasildi/{donus.isoformat()}"})
        for saat in ("09:05", "09:10", "12:05", "17:40"):
            self.assertEqual(self.calistir(saat=saat, gun=donus)[:5], "bitti", saat)
        self.assertEqual(len(S.yayinlar()), 1)

    def test_donus_eski_gun_yayin_kipinde_paylasilamaz(self):
        # Soru 1: tarih elle girilse de eski gün yayın kipinde paylaşılmaz; eski tarihli akşam hazırlığı yalnız kap kurar.
        donus, eski = dt.date(2026, 12, 10), dt.date(2026, 11, 24)
        gun_kur(donus)
        gun_kur(eski)
        self.assertIn("Yalnız bugünün", self.calistir(saat="10:00", girdi="yayin", tarih=eski.isoformat(), gun=donus))
        self.assertIn("Yalnız bugünün", self.calistir(saat="10:00", tarih=eski.isoformat(), gun=donus))
        self.assertEqual(S.ig_yazmalari(), [])
        self.assertEqual(self.calistir(saat="20:00", asama="aksam", tarih=eski.isoformat(), gun=donus), "tamam")
        self.assertEqual(S.yayinlar(), [])

    def test_donus_gunu_elle_paylasilmissa_kilit2_durdurur(self):
        # Soru 2: Rıdvan sabah elle paylaştı, açıklamanın ilk satırı aynı (boşluk farkı önemsiz): iş paylaşmaz ve
        # paylasildi/<gün> yazar. Bu etiket o gün reel ve ek gönderiyi başlatır (test_reel, test_ek).
        self.elle_gonderi(BUGUN, "07:50", ilk_satir="  Bugün ne pişireyim?   DENEME menüsü: çorba, ana yemek, yan yemek, tatlı.")
        self.assertEqual(self.calistir(saat="08:20")[:5], "bitti")
        self.assertEqual(S.yayinlar(), [])
        self.assertIn("paylasildi/2026-11-20", self.etiketler)

    def test_donus_gunu_elle_ilk_satir_farkliysa_cift_paylasim(self):
        # Soru 2 (bilinen risk): elle gönderinin ilk satırı değiştirilmişse kilit 2 tutmaz, gönderi ikinci kez çıkar.
        # Önlem kodda değil, dönüş kuralında (DONUS.md "Dönüş gününde elle paylaşım").
        self.elle_gonderi(BUGUN, "07:50", ilk_satir="Akşama ne var? Bugünün menüsü")
        self.assertEqual(self.calistir(saat="08:20"), "tamam")
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertEqual(len(S.medya), 2)

    def test_donus_gunu_elle_kaydirmali_degilse_cift_paylasim(self):
        # Soru 2 (bilinen risk): kilit 2 yalnız kaydırmalıya (CAROUSEL_ALBUM) bakar; elle tek resim paylaşıldıysa tutmaz.
        self.elle_gonderi(BUGUN, "07:50", tur="IMAGE")
        self.assertEqual(self.calistir(saat="08:20"), "tamam")
        self.assertEqual(len(S.medya), 2)

    def test_donus_aksam_gecisi_ayni_gun_paylasmaz_ertesi_gun_bir_kez(self):
        # Soru 2, önerilen yol: D sabahı son elle paylaşım (ilk satır aynı), D akşamı yayına geçiş. Geciken bir yedek
        # saat (12:05 → 18:30) D'yi yeniden paylaşmaz; 20:00 hazırlığı D+1'i kurar; D+1 09:00'da tek gönderi.
        D, D1 = BUGUN, BUGUN + dt.timedelta(days=1)
        self.elle_gonderi(D, "08:55")
        self.assertEqual(self.calistir(saat="18:30", gun=D)[:5], "bitti")
        self.assertEqual(self.calistir(saat="20:00", asama="aksam", gun=D), "tamam")
        self.assertEqual(self.calistir(saat="08:15", gun=D1), "tamam")
        self.assertEqual(self.calistir(saat="09:05", gun=D1)[:5], "bitti")
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertEqual([m["timestamp"][:16] for m in S.medya], ["2026-11-20T05:55", "2026-11-21T06:00"])

    def test_donus_yedek_saatler_cift_paylasmaz(self):
        # Soru 3: Google 08:15'te başlatır, 09:00'da paylaşır; GitHub yedekleri (09:05, 12:05) ve nöbetçi etiketi görüp çıkar.
        self.assertEqual(self.calistir(saat="08:15"), "tamam")
        for saat in ("09:05", "09:10", "12:05", "17:40"):
            self.assertEqual(self.calistir(saat=saat)[:5], "bitti", saat)
        self.assertEqual(len(S.yayinlar()), 1)

    def test_donus_etiket_yazilamazsa_yedek_saat_kilit2_ile_durur(self):
        # Soru 3: paylaşıldı ama kayıt etiketi yazılamadı (iş kırmızı); 09:05 yedeği gönderiyi Instagram'da bulur.
        paylas.etiket_koy = lambda t, m: False
        self.assertIn("kayıt etiketi yazılamadı", self.calistir(saat="08:15"))
        paylas.etiket_koy = lambda t, m: self.etiketler.add(paylas.etiket_adi(t)) or True
        self.assertEqual(self.calistir(saat="09:05")[:5], "bitti")
        self.assertEqual(len(S.yayinlar()), 1)
        self.assertIn("paylasildi/2026-11-20", self.etiketler)

    def test_donus_kip_sirasi_kontrol_prova_yayin(self):
        # Soru 3: D günü (sabah elle paylaşıldı) 09:20'den sonra elle kontrol, sonra D+1 için prova; D akşamı
        # PAYLASIM_KIPI=yayin. Kontrol Instagram'a yazmaz, prova paylaşmaz, D+1 sabahı hazır kap bir kez paylaşılır.
        D, D1 = BUGUN, BUGUN + dt.timedelta(days=1)
        self.elle_gonderi(D, "08:55")
        self.assertEqual(self.calistir(saat="09:30", girdi="kontrol", ayar="kontrol", gun=D), "tamam")
        self.assertEqual(S.ig_yazmalari(), [])
        self.assertEqual(self.calistir(saat="10:00", girdi="prova", ayar="kontrol", tarih=D1.isoformat(), gun=D), "tamam")
        self.assertEqual(S.yayinlar(), [])
        self.assertIn(D1.isoformat(), self.kap_kayit)
        yazma = len(S.ig_yazmalari())
        self.assertEqual(self.calistir(saat="08:15", ayar="yayin", gun=D1), "tamam")
        self.assertEqual(self.yalniz_yayin(yazma), ["media_publish"])
        self.assertEqual(len(S.medya), 2)

    def test_donus_ayni_gun_prova_sonra_yayina_gecis_o_gun_paylasir(self):
        # Soru 3 (dikkat): tarihsiz prova bugünün kabını kurar; aynı gün yayına geçilirse sonraki tetik (yedek saat ya
        # da nöbetçi) o kabı hemen paylaşır. Bu yüzden dönüş günü prova D+1 tarihiyle yapılır (DONUS.md).
        self.assertEqual(self.calistir(saat="10:00", girdi="prova", ayar="kontrol"), "tamam")
        yazma = len(S.ig_yazmalari())
        self.assertEqual(self.calistir(saat="12:05", ayar="yayin"), "tamam")
        self.assertEqual(self.yalniz_yayin(yazma), ["media_publish"])
        self.assertEqual(len(S.medya), 1)

    def test_donus_prova_onayli_gun_yayinda_durur(self):
        # Soru 3: akşam provasında geçen "yalnız prova" onaylı gün, yayına geçilen sabah hazır kap olsa da paylaşılmaz.
        D1 = BUGUN + dt.timedelta(days=1)
        gun_kur(D1, yalniz_prova=True)
        self.assertEqual(self.calistir(saat="20:00", asama="aksam", ayar="prova"), "tamam")
        self.assertIn("yalnız prova", self.calistir(saat="08:15", ayar="yayin", gun=D1))
        self.assertEqual(S.yayinlar(), [])

    def test_donus_paylasim_kipi_yazimi(self):
        # Soru 3: PAYLASIM_KIPI tam "yayin" olmalı. Boş ya da "yayın" (ı) gibi yanlış yazım kontrole düşer: iş yeşil
        # biter ama paylaşmaz (yalnız uyarı).
        for ayar, kip in (("", "kontrol"), ("yayın", "kontrol"), ("Yayın", "kontrol"), ("yayim", "kontrol"),
                          (" YAYIN ", "yayin"), ("prova", "prova"), ("yayin", "yayin")):
            os.environ.update({"KIP_GIRDI": "otomatik", "KIP_AYARI": ayar})
            with redirect_stdout(io.StringIO()):
                self.assertEqual(paylas.kip_belirle()[0], kip, ayar)
        self.assertEqual(self.calistir(saat="08:20", ayar="yayın"), "tamam")
        self.assertEqual(self.ciktilar["kip"], "kontrol")
        self.assertIn("tanınmadı", self.gunluk)
        self.assertEqual(S.ig_yazmalari(), [])

    def test_donus_kullanilan_uclar(self):
        # Soru 4: yayın kipinde paylaşım işinin Instagram'da kullandığı uçların tamamı (DONUS.md "Anahtar ve izin").
        self.video_kur()
        self.assertEqual(self.calistir(saat="08:20"), "tamam")

        def uc(i):
            yol = re.sub(r"^medya\d+$", "<medya>", re.sub(r"^kap\d+$", "<kap>", i[1]))
            return f"{i[0]} {yol.replace(paylas.IG_ID, '<IG>')}"
        self.assertEqual({uc(i) for i in S.istekler}, {
            "GET <IG>", "GET debug_token", "GET <IG>/content_publishing_limit", "POST <IG>/media",
            "GET <kap>", "GET <IG>/media", "POST <IG>/media_publish", "GET <medya>"})
        self.assertEqual(len(S.yuklemeler), 1)                  # + rupload (kapak videosu doğrudan yükleme)
        turler = {i[2].get("media_type", "IMAGE") for i in S.istekler if i[:2] == ("POST", f"{paylas.IG_ID}/media")}
        self.assertEqual(turler, {"VIDEO", "IMAGE", "CAROUSEL"})

    def test_donus_anahtar_izni_ve_suresi(self):
        # Soru 4: izin yoksa ya da anahtar geçersizse iş başlamaz; süresi 14 günden az kaldıysa uyarır.
        S.anahtar["scopes"] = ["instagram_basic"]
        self.assertIn("instagram_content_publish", self.calistir(saat="20:00", ayar="kontrol"))
        S.anahtar.update(scopes=["instagram_basic", "instagram_content_publish"], is_valid=False)
        self.assertIn("geçersiz", self.calistir(saat="20:00", ayar="kontrol"))
        yakin = int((dt.datetime.combine(BUGUN, dt.time(20, 0), IST) + dt.timedelta(days=5)).timestamp())
        S.anahtar.update(is_valid=True, expires_at=yakin, data_access_expires_at=yakin)
        self.assertEqual(self.calistir(saat="20:00", ayar="kontrol"), "tamam")
        self.assertIn("Anahtarın süresi 14 günden az", self.gunluk)
        self.assertIn("Veri erişiminin süresi 14 günden az", self.gunluk)
        self.assertEqual(S.ig_yazmalari(), [])


if __name__ == "__main__":
    unittest.main()
