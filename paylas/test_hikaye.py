"""paylas/hikaye.py denemeleri (Graph API ve git sahte).  python3 paylas/test_hikaye.py"""
import datetime as dt
import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402
import hikaye as H  # noqa: E402

AD = "2026-11-one-cikan"
OGLEN = dt.datetime(2026, 11, 17, 19, 30, tzinfo=H.IST)


class Sahte:
    def __init__(self, hata_publish=None, durum="FINISHED"):
        self.kaplar, self.yayin, self.etiketler = [], [], set()
        self.hata_publish, self.durum = hata_publish, durum

    def graph(self, yontem, yol, params=None, zaman_asimi=60):
        if yontem == "POST" and yol.endswith("/media"):
            self.kaplar.append(params)
            return {"id": f"k{len(self.kaplar)}"}
        if yontem == "GET":
            return {"status_code": self.durum}
        if yol.endswith("/media_publish"):
            if self.hata_publish:
                raise self.hata_publish
            self.yayin.append(params["creation_id"])
            return {"id": "m" + params["creation_id"]}
        raise AssertionError(yol)


class Deneme(unittest.TestCase):
    def setUp(self):
        self.s = Sahte()
        self.eski = (P.graph, H.etiket_var, H.etiket_yaz, P.uyu, H.ozet)
        P.graph = self.s.graph
        H.etiket_var = lambda ad: ad in self.s.etiketler
        H.etiket_yaz = lambda ad, m: self.s.etiketler.add(ad) or True
        P.uyu = lambda sn: None
        H.ozet = lambda m: None
        os.environ["GITHUB_SHA"] = "abc123"

    def tearDown(self):
        P.graph, H.etiket_var, H.etiket_yaz, P.uyu, H.ozet = self.eski
        os.environ.pop("KIP", None)

    def test_prova_paylasmaz(self):
        os.environ["KIP"] = "prova"
        self.assertEqual(H.calistir(AD, OGLEN), (0, 0))
        self.assertEqual(len(self.s.kaplar), 6)
        self.assertEqual(self.s.yayin, [])
        self.assertTrue(all(k["media_type"] == "STORIES" for k in self.s.kaplar))

    def test_yayin_sirayla_ve_ham_adresle(self):
        os.environ["KIP"] = "yayin"
        self.assertEqual(H.calistir(AD, OGLEN), (6, 0))
        adresler = [k["image_url"] for k in self.s.kaplar]
        self.assertEqual(adresler[0], "https://raw.githubusercontent.com/ridvancoskun1975-cpu/aksama-medya/abc123/hikaye/2026-11-one-cikan/1-nasil-00.jpg")
        self.assertTrue(adresler[-1].endswith("2-olculer-01.jpg"))
        self.assertEqual(len(self.s.etiketler), 6)

    def test_kaldigi_yerden_surer(self):
        os.environ["KIP"] = "yayin"
        self.s.etiketler |= {f"hikaye/{AD}/1-nasil-00", f"hikaye/{AD}/1-nasil-01"}
        self.assertEqual(H.calistir(AD, OGLEN), (4, 2))
        self.assertTrue(self.s.kaplar[0]["image_url"].endswith("1-nasil-02.jpg"))

    def test_sabah_calismaz(self):
        os.environ["KIP"] = "yayin"
        with self.assertRaises(P.Dur):
            H.calistir(AD, dt.datetime(2026, 11, 18, 8, 45, tzinfo=H.IST))
        self.assertEqual(self.s.kaplar, [])

    def test_belirsiz_hatada_durur(self):
        os.environ["KIP"] = "yayin"
        self.s.hata_publish = P.GraphHatasi(500, {"error": {"message": "x"}})
        with self.assertRaises(P.Dur):
            H.calistir(AD, OGLEN)
        self.assertEqual(len(self.s.kaplar), 1)

    def test_gorsel_reddedilirse_durur(self):
        os.environ["KIP"] = "yayin"
        self.s.durum = "ERROR"
        with self.assertRaises(P.Dur):
            H.calistir(AD, OGLEN)
        self.assertEqual(self.s.yayin, [])


if __name__ == "__main__":
    unittest.main()
