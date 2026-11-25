"""Reel paylaşımının denemesi: sahte Instagram (Graph ve video yükleme), sahte etiket, sahte saat.
Gerçek hesaba ve gerçek depoya hiçbir şey gönderilmez.
Çalıştırma: python3 paylas/test_reel.py -v
"""
import datetime as dt
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout

os.environ["IG_TOKEN"] = "sahte"
os.environ.pop("GITHUB_STEP_SUMMARY", None)
os.environ.pop("GITHUB_OUTPUT", None)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402
import reel as R    # noqa: E402

GECICI = pathlib.Path(tempfile.mkdtemp(prefix="aksama-reel-deneme-"))
TARIH = "2026-11-17"
GUN = GECICI / TARIH
GUN.mkdir()
(GUN / "gun.json").write_text(json.dumps({"tarih_yazi": "17 Kasım 2026", "yemekler": [
    {"tur": "Çorba", "ad": "Karnabahar Çorbası"}, {"tur": "Ana yemek", "ad": "Kıymalı Ispanak"},
    {"tur": "Yan yemek", "ad": "Pirinç Pilavı"}, {"tur": "Tatlı", "ad": "Sütlaç"}]}), encoding="utf-8")
VIDEO = GECICI / "reel.mp4"
VIDEO.write_bytes(b"x" * 1234)
YAN = GECICI / "reel.json"
YUKLEME_ADRESI = "https://rupload.facebook.com/ig-api-upload/v26.0/kap"


class Sahte:
    def __init__(self):
        self.saat = 0.0
        self.istekler = []
        self.medya = []                # Instagram'daki son paylaşımlar
        self.kap_durumlari = []        # sırayla dönecek status_code'lar
        self.yayin_hatalari = []       # media_publish'te sırayla atılacak hatalar
        self.etiketler = []
        self.yuklemeler = []           # (adres, bayt, başlıklar)
        self.yukleme_hatalari = []     # yüklemede sırayla atılacak hatalar ya da dönecek cevaplar
        self.kap_sayisi = 0
        self.uri_ver = True

    def ham_yukle(self, adres, veri, basliklar):
        self.yuklemeler.append((adres, len(veri), dict(basliklar)))
        if self.yukleme_hatalari:
            h = self.yukleme_hatalari.pop(0)
            if isinstance(h, dict):
                return h
            raise h
        return {"success": True, "message": "Upload successful."}

    def graph(self, yontem, yol, params=None, zaman_asimi=60):
        self.istekler.append((yontem, yol, dict(params or {})))
        if yontem == "GET" and yol.endswith("/media"):
            return {"data": list(self.medya)}
        if yontem == "POST" and yol.endswith("/media"):
            self.kap_sayisi += 1
            kap = f"kap{self.kap_sayisi}"
            return {"id": kap, "uri": f"{YUKLEME_ADRESI[:-3]}{kap}"} if self.uri_ver else {"id": kap}
        if yontem == "GET" and yol.startswith("kap"):
            kod = self.kap_durumlari.pop(0) if self.kap_durumlari else "FINISHED"
            return {"status_code": kod, "status": kod}
        if yontem == "POST" and yol.endswith("/media_publish"):
            if self.yayin_hatalari:
                h = self.yayin_hatalari.pop(0)
                if h == "gitti":     # hata döndü ama paylaşım aslında gitmiş
                    self.medya.append(self.reel_kaydi())
                    raise P.GraphHatasi(500, {"error": {"message": "sunucu", "code": 2}})
                raise h
            self.medya.append(self.reel_kaydi())
            return {"id": "m1"}
        if yontem == "GET" and yol in ("m1", "m0"):
            return {"permalink": f"https://www.instagram.com/reel/{yol}/", "timestamp": "2026-11-17T06:05:00+0000"}
        raise AssertionError(f"beklenmeyen istek {yontem} {yol}")

    def reel_kaydi(self, mid="m1"):
        g = json.loads((GUN / "gun.json").read_text(encoding="utf-8"))
        return {"id": mid, "caption": R.aciklama(g), "media_type": "VIDEO", "media_product_type": "REELS",
                "timestamp": "2026-11-17T06:05:00+0000"}

    def yayinlar(self):
        return [i for i in self.istekler if i[1].endswith("/media_publish")]

    def kaplar(self):
        return [i for i in self.istekler if i[0] == "POST" and i[1].endswith("/media")]


class ReelDeneme(unittest.TestCase):
    def setUp(self):
        self.s = s = Sahte()
        self.eski = (P.graph, P.uyu, P.zaman, R.ham_yukle, R.etiket_yaz, R.INSTAGRAMA_PAYLAS, P.simdi)
        P.graph = s.graph
        P.simdi = lambda: self.an                  # sahte saat: TARIH günü 10:00 (yayında yalnız bugünün reel'i)
        self.an = dt.datetime(2026, 11, 17, 10, 0, tzinfo=R.IST)
        P.uyu = lambda sn: setattr(s, "saat", s.saat + sn)
        P.zaman = lambda: s.saat
        R.ham_yukle = s.ham_yukle
        R.etiket_yaz = lambda tarih, mesaj: (s.etiketler.append((tarih, mesaj)), True)[1]
        YAN.write_text(json.dumps({"muzik": "Cotton Sky", "dosya": "cotton-sky.m4a"}), encoding="utf-8")
        os.environ["KIP"] = "yayin"
        os.environ.pop("YZ_ETIKETI", None)
        sys.argv = ["reel.py", "paylas", TARIH, str(GUN), str(VIDEO)]

    def tearDown(self):
        P.graph, P.uyu, P.zaman, R.ham_yukle, R.etiket_yaz, R.INSTAGRAMA_PAYLAS, P.simdi = self.eski

    def calis(self):
        cikti = io.StringIO()
        kod = 0
        with redirect_stdout(cikti):
            try:
                R.calistir("paylas")
            except SystemExit as e:
                kod = e.code
        return kod, cikti.getvalue()

    def test_paylasir_ve_etiket_yazar(self):
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yayinlar()), 1)
        prm = self.s.kaplar()[0][2]
        self.assertEqual(prm["media_type"], "REELS")
        self.assertEqual(prm["upload_type"], "resumable")
        self.assertNotIn("video_url", prm)            # video açık adrese konmaz (müzik lisansı)
        self.assertEqual(prm["audio_name"], "Cotton Sky")
        self.assertEqual(prm["share_to_feed"], "false")    # reel ana ızgaraya girmez (Rıdvan 23 Kas 12:52)
        self.assertEqual(len(self.s.yuklemeler), 1)
        adres, bayt, bas = self.s.yuklemeler[0]
        self.assertEqual(adres, YUKLEME_ADRESI + "1")
        self.assertEqual(bayt, 1234)
        self.assertEqual(bas["Authorization"], "OAuth sahte")
        self.assertEqual((bas["offset"], bas["file_size"]), ("0", "1234"))
        self.assertNotIn("is_ai_generated", prm)
        self.assertIn(P.YZ_SATIRI, prm["caption"])
        self.assertIn(P.TELIF_SATIRI, prm["caption"])
        self.assertIn("takip edin", prm["caption"])
        self.assertEqual(self.s.etiketler[0][0], TARIH)
        self.assertIn("Reel paylaşıldı", cikti)

    def test_etiketler_bes_ve_dogru(self):
        g = json.loads((GUN / "gun.json").read_text(encoding="utf-8"))
        e = R.etiketler(g).split()
        self.assertEqual(e, ["#yemektarifleri", "#evyemekleri", "#kolaytarifler", "#kıymalııspanak", "#akşamanevar"])
        self.assertLessEqual(len(e), 5)

    def test_instagramda_varsa_yeniden_paylasmaz(self):
        self.s.medya.append(self.s.reel_kaydi("m0"))
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(self.s.kaplar(), [])
        self.assertEqual(self.s.yuklemeler, [])
        self.assertEqual(self.s.yayinlar(), [])
        self.assertIn("m0", self.s.etiketler[0][1])

    def test_dunku_reel_engel_olmaz(self):
        dun = self.s.reel_kaydi("m0")
        dun["timestamp"] = "2026-11-16T06:05:00+0000"
        self.s.medya.append(dun)
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yayinlar()), 1)

    def test_prova_paylasmaz(self):
        os.environ["KIP"] = "prova"
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.kaplar()), 1)
        self.assertEqual(self.s.kaplar()[0][2]["share_to_feed"], "false")   # provada da ızgaraya girmez
        self.assertEqual(len(self.s.yuklemeler), 1)
        self.assertEqual(self.s.yayinlar(), [])
        self.assertEqual(self.s.etiketler, [])
        self.assertIn("Cotton Sky", cikti)

    def test_video_reddedilirse_durur(self):
        self.s.kap_durumlari = ["IN_PROGRESS", "ERROR"]
        kod, cikti = self.calis()
        self.assertEqual(kod, 1)
        self.assertEqual(self.s.yayinlar(), [])
        self.assertIn("kabul etmedi", cikti)

    def test_islem_uzarsa_bekler(self):
        self.s.kap_durumlari = ["IN_PROGRESS"] * 5
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yayinlar()), 1)

    def test_belirsiz_hatada_iki_kez_paylasmaz(self):
        self.s.yayin_hatalari = ["gitti"]
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yayinlar()), 1)
        self.assertIn("önceki denemede gitmiş", cikti)

    def test_kalici_hatada_durur(self):
        self.s.yayin_hatalari = [P.GraphHatasi(400, {"error": {"message": "izin yok", "code": 10}})]
        kod, cikti = self.calis()
        self.assertEqual(kod, 1)
        self.assertEqual(self.s.etiketler, [])

    def test_yukleme_gecici_hatada_yeni_kapla_dener(self):
        self.s.yukleme_hatalari = [P.GraphHatasi(None, {"error": {"message": "koptu"}}, ag=True)]
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.kaplar()), 2)
        self.assertEqual(len(self.s.yuklemeler), 2)
        self.assertEqual(self.s.yuklemeler[1][0], YUKLEME_ADRESI + "2")
        self.assertEqual(len(self.s.yayinlar()), 1)

    def test_yukleme_basarisiz_cevabinda_yeniden_dener(self):
        self.s.yukleme_hatalari = [{"success": False, "message": "hata"}]
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yuklemeler), 2)
        self.assertEqual(len(self.s.yayinlar()), 1)

    def test_yukleme_kalici_hatada_durur(self):
        self.s.yukleme_hatalari = [P.GraphHatasi(400, {"error": {"message": "izin yok", "code": 10}})]
        kod, cikti = self.calis()
        self.assertEqual(kod, 1)
        self.assertEqual(len(self.s.kaplar()), 1)
        self.assertEqual(self.s.yayinlar(), [])
        self.assertEqual(self.s.etiketler, [])

    def test_uri_gelmezse_adres_kurulur(self):
        self.s.uri_ver = False
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(self.s.yuklemeler[0][0], YUKLEME_ADRESI + "1")

    def test_muzik_adi_yoksa_ses_adi_konmaz(self):
        YAN.unlink()
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertNotIn("audio_name", self.s.kaplar()[0][2])

    def test_ozel_gunde_tebrik_ilk_satir(self):
        YAN.write_text(json.dumps({"muzik": "Nikriz Longa", "tebrik": "Regaip Kandiliniz mübarek olsun. Rahmet gecesi."},
                                  ensure_ascii=False), encoding="utf-8")
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        satir = self.s.kaplar()[0][2]["caption"].split("\n")
        self.assertEqual(satir[0], "Regaip Kandiliniz mübarek olsun. Rahmet gecesi.")
        self.assertTrue(satir[1].startswith("Bugün ne yemek yapayım? Menü hazır:"))

    def test_siradan_gunde_tebrik_yok(self):
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertTrue(self.s.kaplar()[0][2]["caption"].startswith("Bugün ne yemek yapayım? Menü hazır:"))

    def test_video_yoksa_durur(self):
        sys.argv[4] = str(GECICI / "yok.mp4")
        kod, cikti = self.calis()
        self.assertEqual(kod, 1)
        self.assertEqual(self.s.kaplar(), [])
        self.assertIn("Video yok", cikti)

    def test_kapali_anahtar(self):
        R.INSTAGRAMA_PAYLAS = False
        kod, cikti = self.calis()
        self.assertEqual(kod, 0)
        self.assertEqual(self.s.istekler, [])

    def test_yz_etiketi(self):
        os.environ["YZ_ETIKETI"] = "evet"
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(self.s.kaplar()[0][2].get("is_ai_generated"), "true")

    # --- otomatiğe dönüş (DONUS.md) ---
    def test_donus_elle_reel_ilk_satir_farkliysa_ikinci_reel_gider(self):
        # Soru 2 (bilinen risk): Rıdvan aynı gün reel'i de elle paylaştıysa ve açıklamanın ilk satırı otomatik reel'inkiyle
        # aynı değilse kilit 2 tutmaz, ikinci reel çıkar (aynıysa çıkmaz: test_instagramda_varsa_yeniden_paylasmaz).
        elle = self.s.reel_kaydi("m0")
        elle["caption"] = "Akşama ne var? Bugünün menüsü\n#akşamanevar"
        self.s.medya.append(elle)
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yayinlar()), 1)

    def test_donus_kullanilan_uclar(self):
        # Soru 4: reel işinin Instagram'da kullandığı uçlar (+ rupload.facebook.com doğrudan yükleme).
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        uclar = {(y, re.sub(r"^(kap|m)\d+$", r"<\1>", p).replace(P.IG_ID, "<IG>")) for y, p, _ in self.s.istekler}
        self.assertEqual(uclar, {("GET", "<IG>/media"), ("POST", "<IG>/media"), ("GET", "<kap>"),
                                 ("POST", "<IG>/media_publish"), ("GET", "<m>")})
        self.assertTrue(self.s.yuklemeler[0][0].startswith("https://rupload.facebook.com/ig-api-upload/v26.0/"))

    def test_donus_eski_gun_yayin_kipinde_reel_paylasilmaz(self):
        # Açık (a), kapandı: saat 10 Ara 10:00, elle tarih 16 Kas, kip yayin. Eski günün reel'i gitmez; paylas.py'deki
        # eski gün korumasıyla aynı: iş kırmızı biter (::error::), Instagram'a hiçbir istek gitmez, etiket yazılmaz.
        self.an = dt.datetime(2026, 12, 10, 10, 0, tzinfo=R.IST)
        sys.argv = ["reel.py", "paylas", "2026-11-16", str(GUN), str(VIDEO)]
        kod, cikti = self.calis()
        self.assertEqual(kod, 1, cikti)
        self.assertIn("::error::Yalnız bugünün reel'i", cikti)
        self.assertEqual(self.s.istekler, [])
        self.assertEqual(self.s.yuklemeler, [])
        self.assertEqual(self.s.yayinlar(), [])
        self.assertEqual(self.s.etiketler, [])

    def test_donus_eski_gun_provada_serbest(self):
        # Prova (ve yayin dışındaki her kip) eski tarihle çalışır: kap kurulur, video yüklenir, paylaşılmaz.
        self.an = dt.datetime(2026, 12, 10, 10, 0, tzinfo=R.IST)
        sys.argv = ["reel.py", "paylas", "2026-11-16", str(GUN), str(VIDEO)]
        for kip in ("prova", "kontrol"):
            os.environ["KIP"] = kip
            kod, cikti = self.calis()
            self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.kaplar()), 2)
        self.assertEqual(self.s.yayinlar(), [])
        self.assertEqual(self.s.etiketler, [])


class SabitSaat(dt.datetime):
    an = None

    @classmethod
    def now(cls, tz=None):
        return cls.an


class DonusGerek(unittest.TestCase):
    """Reel işinin "gerek var mı" adımı uzun aradan sonra (DONUS.md). Etiketler GitHub'daki 25 Kas durumu:
    paylasildi/ 16–20 Kas, reel/ 17–20 Kas; elle paylaşılan günlerde (24 Kas–) etiket yok."""
    DONUS = dt.datetime(2026, 12, 10, 9, 25, tzinfo=R.IST)

    def setUp(self):
        self.etiketler = ({f"paylasildi/2026-11-{g}" for g in (16, 17, 18, 19, 20)}
                          | {f"reel/2026-11-{g}" for g in (17, 18, 19, 20)})
        self.eski = (R.etiket_var, R.dt)
        R.etiket_var = lambda ad: ad in self.etiketler
        R.dt = types.SimpleNamespace(datetime=SabitSaat, date=dt.date, time=dt.time, timezone=dt.timezone,
                                     timedelta=dt.timedelta)
        self.cikti = GECICI / "gerek-cikti.txt"
        os.environ.update({"GITHUB_OUTPUT": str(self.cikti), "OLAY": "workflow_dispatch", "KIP": "yayin"})

    def tearDown(self):
        R.etiket_var, R.dt = self.eski
        for ad in ("GITHUB_OUTPUT", "OLAY", "TARIH_GIRDI"):
            os.environ.pop(ad, None)

    def gerek(self, an, tarih=""):
        SabitSaat.an = an
        os.environ["TARIH_GIRDI"] = tarih
        self.cikti.write_text("")
        with redirect_stdout(io.StringIO()):
            R.gerek()
        return dict(s.split("=", 1) for s in self.cikti.read_text().splitlines() if "=" in s)

    def test_donus_yalniz_bugun_eski_gunlere_gecmez(self):
        # Soru 1: otomatik tetik (tarihsiz) yalnız bugüne bakar; bugünün gönderisi çıkmadan reel yok.
        self.assertEqual(self.gerek(self.DONUS)["gerek"], "hayir")
        # Soru 2: gönderi elle paylaşılmış ve paylaşım işinin kilit 2'si etiketi yazmışsa reel o gün hazırlanır.
        self.etiketler.add("paylasildi/2026-12-10")
        c = self.gerek(self.DONUS)
        self.assertEqual((c["gerek"], c["tarih"], c["kip"]), ("evet", "2026-12-10", "yayin"))

    def test_donus_elle_paylasilan_gun_icin_reel_yok(self):
        # Soru 1: elle paylaşılan günlerin etiketi yok; tarih girilse de reel hazırlanmaz. Yayın kipinde eski tarih
        # zaten durur (test_donus_eski_gun_elle_tarihle_reel_yok); provada da etiket olmadığı için reel yok.
        with self.assertRaises(P.Dur):
            self.gerek(self.DONUS, "2026-11-24")
        os.environ["KIP"] = "prova"
        self.assertEqual(self.gerek(self.DONUS, "2026-11-24")["gerek"], "hayir")

    def test_donus_eski_gun_elle_tarihle_reel_yok(self):
        # Açık (a), kapandı: elle başlatılıp eski tarih girilirse (gönderisi çıkmış, reel'i çıkmamış 16 Kas; saat 10 Ara
        # 10:00) yayın kipinde iş kırmızı biter, "gerek" çıktısı yazılmaz; sonraki adımlar (video, reel, ek) çalışmaz.
        SabitSaat.an = dt.datetime(2026, 12, 10, 10, 0, tzinfo=R.IST)
        for tarih in ("2026-11-16", "2026-11-17"):
            os.environ["TARIH_GIRDI"] = tarih
            self.cikti.write_text("")
            out = io.StringIO()
            with redirect_stdout(out), self.assertRaises(SystemExit) as s:
                R.calistir("gerek")
            self.assertEqual(s.exception.code, 1)
            self.assertIn("::error::Yalnız bugünün reel'i", out.getvalue())
            self.assertNotIn("gerek=", self.cikti.read_text())
        # Prova kipinde eski tarih serbest (gönderisi paylaşılmış gün için).
        os.environ["KIP"] = "prova"
        c = self.gerek(SabitSaat.an, "2026-11-16")
        self.assertEqual((c["gerek"], c["tarih"], c["kip"]), ("evet", "2026-11-16", "prova"))

    def test_donus_bugunun_tarihi_elle_girilirse_reel_hazirlanir(self):
        # Koruma yalnız eski/ileri tarihi keser: bugünün tarihi elle girilirse yayın kipinde reel hazırlanır.
        self.etiketler.add("paylasildi/2026-12-10")
        c = self.gerek(dt.datetime(2026, 12, 10, 10, 0, tzinfo=R.IST), "2026-12-10")
        self.assertEqual((c["gerek"], c["tarih"], c["kip"]), ("evet", "2026-12-10", "yayin"))
        with self.assertRaises(P.Dur):
            self.gerek(dt.datetime(2026, 12, 10, 10, 0, tzinfo=R.IST), "2026-12-11")

    def test_donus_sabah_penceresinde_elle_reel_yok(self):
        # Soru 3: 08:00–09:20 arasında elle reel denemesi yapılmaz (09:00 gönderisi korunur).
        self.etiketler.add("paylasildi/2026-12-10")
        self.assertEqual(self.gerek(dt.datetime(2026, 12, 10, 8, 45, tzinfo=R.IST))["gerek"], "hayir")


if __name__ == "__main__":
    unittest.main()
