"""Reel paylaşımının denemesi: sahte Instagram (Graph), sahte Pages, sahte etiket, sahte saat.
Gerçek hesaba ve gerçek depoya hiçbir şey gönderilmez.
Çalıştırma: python3 paylas/test_reel.py -v
"""
import datetime as dt
import io
import json
import os
import pathlib
import sys
import tempfile
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


class Sahte:
    def __init__(self):
        self.saat = 0.0
        self.istekler = []
        self.medya = []                # Instagram'daki son paylaşımlar
        self.kap_durumlari = []        # sırayla dönecek status_code'lar
        self.yayin_hatalari = []       # media_publish'te sırayla atılacak hatalar
        self.etiketler = []
        self.pages_boyut = [1234]      # sırayla dönecek boyutlar (son değer kalır)

    def graph(self, yontem, yol, params=None, zaman_asimi=60):
        self.istekler.append((yontem, yol, dict(params or {})))
        if yontem == "GET" and yol.endswith("/media"):
            return {"data": list(self.medya)}
        if yontem == "POST" and yol.endswith("/media"):
            return {"id": "kap1"}
        if yontem == "GET" and yol == "kap1":
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
        self.eski = (P.graph, P.uyu, P.zaman, R.boyut_oku, R.etiket_yaz, R.INSTAGRAMA_PAYLAS)
        P.graph = s.graph
        P.uyu = lambda sn: setattr(s, "saat", s.saat + sn)
        P.zaman = lambda: s.saat
        R.boyut_oku = lambda adres: s.pages_boyut.pop(0) if len(s.pages_boyut) > 1 else s.pages_boyut[0]
        R.etiket_yaz = lambda tarih, mesaj: (s.etiketler.append((tarih, mesaj)), True)[1]
        os.environ["SAYFA_ADRESI"] = "https://ornek.github.io/aksama-medya/"
        os.environ["KIP"] = "yayin"
        os.environ.pop("YZ_ETIKETI", None)
        sys.argv = ["reel.py", "paylas", TARIH, str(GUN), str(VIDEO)]

    def tearDown(self):
        P.graph, P.uyu, P.zaman, R.boyut_oku, R.etiket_yaz, R.INSTAGRAMA_PAYLAS = self.eski

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
        self.assertEqual(prm["video_url"], "https://ornek.github.io/aksama-medya/reel.mp4")
        self.assertEqual(prm["share_to_feed"], "true")
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
        self.assertEqual(self.s.yayinlar(), [])
        self.assertEqual(self.s.etiketler, [])

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

    def test_video_pagese_gelmezse_durur(self):
        self.s.pages_boyut = [None]
        kod, cikti = self.calis()
        self.assertEqual(kod, 1)
        self.assertEqual(self.s.kaplar(), [])
        self.assertIn("Pages", cikti)

    def test_video_gec_gelirse_bekler(self):
        self.s.pages_boyut = [None, 99, 1234]
        kod, cikti = self.calis()
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(len(self.s.yayinlar()), 1)

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


if __name__ == "__main__":
    unittest.main()
