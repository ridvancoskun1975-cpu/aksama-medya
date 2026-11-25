"""paylas/ek.py denemeleri (Graph API ve git sahte; gerçek ek/ klasörüyle).  python3 paylas/test_ek.py"""
import datetime as dt
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402
import hikaye as H  # noqa: E402
import ek as E  # noqa: E402

AD = "2026-11-tanitim"
GUN = dt.date(2026, 11, 19)
SABAH = dt.datetime(2026, 11, 19, 9, 27, tzinfo=E.IST)


class Sahte:
    def __init__(self):
        self.kaplar, self.yayin, self.medya = [], [], []
        self.etiketler = {f"paylasildi/{GUN.isoformat()}"}
        self.hata_publish = None

    def graph(self, yontem, yol, params=None, zaman_asimi=60):
        if yontem == "POST" and yol.endswith("/media"):
            self.kaplar.append(params)
            return {"id": f"k{len(self.kaplar)}"}
        if yontem == "POST" and yol.endswith("/media_publish"):
            if self.hata_publish:
                h, self.hata_publish = self.hata_publish, None
                self.medya.insert(0, {"id": "m-gitti", "media_type": "CAROUSEL_ALBUM", "caption": self.kaplar[-1]["caption"],
                                      "timestamp": "2026-11-19T06:27:00+0000"})
                raise h
            self.yayin.append(params["creation_id"])
            return {"id": "m" + params["creation_id"]}
        if yontem == "GET" and yol.endswith("/media"):
            return {"data": self.medya[:int((params or {}).get("limit", 25))]}
        if yontem == "GET":
            if "permalink" in (params or {}).get("fields", ""):
                return {"permalink": "https://www.instagram.com/p/x/", "timestamp": "t"}
            return {"status_code": "FINISHED"}
        raise AssertionError(yol)


class Deneme(unittest.TestCase):
    def setUp(self):
        self.s = Sahte()
        self.eski = (P.graph, H.etiket_var, H.etiket_yaz, P.uyu, E.ozet, P.uyari)
        P.graph = self.s.graph
        H.etiket_var = lambda ad: ad in self.s.etiketler
        H.etiket_yaz = lambda ad, m: self.s.etiketler.add(ad) or True
        P.uyu = lambda sn: None
        E.ozet = lambda m: None
        P.uyari = lambda m: None
        os.environ["GITHUB_SHA"] = "abc123"
        os.environ.pop("YZ_ETIKETI", None)

    def tearDown(self):
        P.graph, H.etiket_var, H.etiket_yaz, P.uyu, E.ozet, P.uyari = self.eski
        os.environ.pop("KIP", None)
        E.KOK = pathlib.Path(E.__file__).resolve().parent.parent

    def test_gercek_klasor_onayli(self):
        d = E.oku(E.KOK / "ek" / AD)
        self.assertEqual(len(d["kareler"]), 4)
        self.assertEqual(d["tarih"], GUN)
        self.assertTrue(d["aciklama"].startswith("Bugün ne yemek yapayım?"))

    def test_yayin_paylasir_ve_kilitler(self):
        os.environ["KIP"] = "yayin"
        self.assertEqual(E.calistir(SABAH), [(AD, "paylasildi")])
        cocuk, ana = self.s.kaplar[:4], self.s.kaplar[4]
        self.assertEqual(cocuk[0]["image_url"], "https://raw.githubusercontent.com/ridvancoskun1975-cpu/aksama-medya/abc123/ek/2026-11-tanitim/kareler/01-kanca.jpg")
        self.assertTrue(all(c["is_carousel_item"] == "true" and c["alt_text"] for c in cocuk))
        self.assertEqual(ana["media_type"], "CAROUSEL")
        self.assertEqual(ana["children"], "k1,k2,k3,k4")
        self.assertNotIn("is_ai_generated", ana)
        self.assertEqual(self.s.yayin, ["k5"])
        self.assertIn(f"ek/{AD}", self.s.etiketler)
        # ikinci çalıştırma: kilit
        self.assertEqual(E.calistir(SABAH), [(AD, "onceden")])
        self.assertEqual(self.s.yayin, ["k5"])

    def test_tarihten_once_paylasmaz(self):
        os.environ["KIP"] = "yayin"
        dun = dt.datetime(2026, 11, 18, 9, 40, tzinfo=E.IST)
        self.s.etiketler.add("paylasildi/2026-11-18")
        self.assertEqual(E.calistir(dun), [(AD, "vakti-yok")])
        self.assertEqual(self.s.kaplar, [])

    def test_sabah_gonderisi_yoksa_beklenir(self):
        os.environ["KIP"] = "yayin"
        self.s.etiketler.clear()
        self.assertEqual(E.calistir(SABAH), [(AD, "sabah-yok")])
        self.assertEqual(self.s.kaplar, [])

    def test_saat_disinda_calismaz(self):
        os.environ["KIP"] = "yayin"
        self.assertEqual(E.calistir(dt.datetime(2026, 11, 19, 9, 5, tzinfo=E.IST)), [])
        self.assertEqual(E.calistir(dt.datetime(2026, 11, 19, 20, 30, tzinfo=E.IST)), [])
        self.assertEqual(self.s.kaplar, [])

    def test_ertesi_gun_de_paylasir(self):
        os.environ["KIP"] = "yayin"
        self.s.etiketler.add("paylasildi/2026-11-20")
        self.assertEqual(E.calistir(dt.datetime(2026, 11, 20, 9, 30, tzinfo=E.IST)), [(AD, "paylasildi")])

    def test_instagramda_varsa_yeniden_paylasmaz(self):
        os.environ["KIP"] = "yayin"
        metin = (E.KOK / "ek" / AD / "aciklama.txt").read_text(encoding="utf-8")
        self.s.medya = [{"id": "m-eski", "media_type": "CAROUSEL_ALBUM", "caption": metin,
                         "timestamp": "2026-11-19T06:30:00+0000"}]
        self.assertEqual(E.calistir(SABAH), [(AD, "onceden")])
        self.assertEqual(self.s.kaplar, [])
        self.assertIn(f"ek/{AD}", self.s.etiketler)

    def test_gunluk_gonderi_kilit_sayilmaz(self):
        os.environ["KIP"] = "yayin"
        self.s.medya = [{"id": "m-gun", "media_type": "CAROUSEL_ALBUM", "caption": "Bugün ne pişirsem? Menü hazır.\n...",
                         "timestamp": "2026-11-19T06:00:00+0000"}]
        self.assertEqual(E.calistir(SABAH), [(AD, "paylasildi")])

    def test_belirsiz_hatada_gittiyse_ikinci_kez_gitmez(self):
        os.environ["KIP"] = "yayin"
        self.s.hata_publish = P.GraphHatasi(500, {"error": {"message": "x"}})
        self.assertEqual(E.calistir(SABAH), [(AD, "paylasildi")])
        self.assertEqual(self.s.yayin, [])          # ikinci media_publish yok
        self.assertIn(f"ek/{AD}", self.s.etiketler)

    def test_prova_paylasmaz_tarihe_bakmaz(self):
        os.environ["KIP"] = "prova"
        self.s.etiketler.clear()
        sonuc = E.calistir(dt.datetime(2026, 11, 18, 10, 0, tzinfo=E.IST))
        self.assertEqual(sonuc, [(AD, "prova")])
        self.assertEqual(len(self.s.kaplar), 5)
        self.assertEqual(self.s.yayin, [])
        self.assertNotIn(f"ek/{AD}", self.s.etiketler)

    def test_yz_etiketi(self):
        os.environ["KIP"] = "prova"
        os.environ["YZ_ETIKETI"] = "evet"
        E.calistir(SABAH)
        self.assertEqual(self.s.kaplar[4]["is_ai_generated"], "true")

    def test_degisen_kare_onaysiz(self):
        gecici = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree(E.KOK / "ek", gecici / "ek")
            k = gecici / "ek" / AD / "aciklama.txt"
            k.write_text(k.read_text(encoding="utf-8") + " ", encoding="utf-8")
            E.KOK = gecici
            os.environ["KIP"] = "yayin"
            with self.assertRaises(P.Dur):
                E.calistir(SABAH)
            self.assertEqual(self.s.kaplar, [])
        finally:
            shutil.rmtree(gecici)

    def test_alt_metin_sayisi(self):
        gecici = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree(E.KOK / "ek", gecici / "ek")
            j = gecici / "ek" / AD / "ek.json"
            e = json.loads(j.read_text(encoding="utf-8"))
            e["alt_metinler"] = e["alt_metinler"][:3]
            j.write_text(json.dumps(e), encoding="utf-8")
            with self.assertRaises(P.Dur):
                E.oku(gecici / "ek" / AD)
        finally:
            shutil.rmtree(gecici)

    # --- otomatiğe dönüş (DONUS.md) ---
    DONUS = dt.datetime(2026, 12, 10, 9, 30, tzinfo=E.IST)

    def test_donus_etiketli_tanitim_yeniden_gitmez(self):
        # Soru 1: depodaki tek ek gönderinin (ek/2026-11-tanitim) etiketi GitHub'da var (25 Kas); dönüş günü yeniden gitmez.
        os.environ["KIP"] = "yayin"
        self.s.etiketler |= {f"ek/{AD}", "paylasildi/2026-12-10"}
        self.assertEqual(E.calistir(self.DONUS), [(AD, "onceden")])
        self.assertEqual(self.s.kaplar, [])

    def test_donus_elle_gunde_ek_gitmez(self):
        # Soru 1–2: günün gönderisinin etiketi yoksa (elle paylaşılan günler) ek gönderi çıkmaz.
        os.environ["KIP"] = "yayin"
        self.s.etiketler = set()
        self.assertEqual(E.calistir(self.DONUS), [(AD, "sabah-yok")])
        self.assertEqual(self.s.kaplar, [])

    def test_donus_etiketsiz_eski_ek_donus_gunu_gider(self):
        # Soru 1 (tasarım gereği, dikkat): etiketi olmayan ek gönderi, tarihi geçmiş olsa da dönüş günü günün
        # gönderisinden sonra bir kez gider. Instagram'da var ama son 25 paylaşımın gerisinde kaldıysa kilit 2 görmez.
        os.environ["KIP"] = "yayin"
        self.s.etiketler = {"paylasildi/2026-12-10"}
        metin = (E.KOK / "ek" / AD / "aciklama.txt").read_text(encoding="utf-8")
        self.s.medya = [{"id": f"m{i}", "media_type": "CAROUSEL_ALBUM", "caption": f"Gün {i}",
                         "timestamp": "2026-12-01T06:00:00+0000"} for i in range(25)]
        self.s.medya.append({"id": "m-tanitim", "media_type": "CAROUSEL_ALBUM", "caption": metin,
                             "timestamp": "2026-11-19T06:30:00+0000"})
        self.assertEqual(E.calistir(self.DONUS), [(AD, "paylasildi")])
        self.assertEqual(len(self.s.yayin), 1)


if __name__ == "__main__":
    unittest.main()
