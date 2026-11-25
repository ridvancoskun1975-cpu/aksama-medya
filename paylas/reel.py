"""Günlük reel: video üretilir ve Instagram'a kendiliğinden, doğrudan yüklenerek paylaşılır (iş akışı: .github/workflows/reel.yml).

Rıdvan 17 Kas 01:54: "Ben uğraşmak istemiyorum, sen yap." · "Edits iptal"
Rıdvan 17 Kas 14:58 (Meta Sound Collection'dan 8 parça): "bu müzikleri kullanacağız random olarak"

  python3 paylas/reel.py gerek                          bugünün gönderisi paylaşıldı mı, reel paylaşılmış mı, saat uygun mu
  python3 paylas/reel.py paylas <tarih> <gün> <video>   Instagram'a reel (kip prova: kap kurulur, video yüklenir, paylaşılmaz)

Reel yalnız o günün onaylı gönderisi paylaşıldıktan sonra (etiket paylasildi/<tarih>) ve aynı menüden üretilir.
Kilitler: kayıt etiketi reel/<tarih> ve Instagram'daki son paylaşımlar (aynı gün, aynı ilk satır) — aynı reel iki kez gitmez.
Müzik videonun içinde (aksama-bot/uretim/reel.py). Lisans yalnız Meta ürünlerini kapsar: video hiçbir açık adrese
(Pages vb.) konmaz, Meta'ya doğrudan yüklenir (resumable upload, rupload.facebook.com). Parçanın adı Instagram'da
ses adı olur (videonun yanındaki .json). Açık depo: günlüğe menü ve açıklama yazılmaz.
"""
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402  (Graph API yardımcıları, kilitler, süreler)

IST = dt.timezone(dt.timedelta(hours=3))
OTO_ARALIK = (dt.time(8, 30), dt.time(19, 30))   # reel yalnız gündüz
YASAK = (dt.time(8, 0), dt.time(9, 20))           # elle deneme yok (09:00 korunur)
RUPLOAD = os.environ.get("RUPLOAD_ADRESI", "https://rupload.facebook.com/ig-api-upload")
YZ_SATIRI = "Görseller temsilidir, yapay zekâ ile hazırlanmıştır."
TELIF_SATIRI = "Bu içerik Akşama Ne Var?™ sayfasına aittir. İzinsiz kopyalanamaz, başka sayfada yayımlanamaz."
# Hashtag (Rıdvan 17 Kas 01:57: "Takipçi kazanma odaklı. Hashtagler dikkat!!"): Instagram en çok 5 izin veriyor
# (Aralık 2025). Konuya uyan, aranan etiketler; genel ya da ilgisiz etiket yok. Türkçe harfsiz yazılanlar
# (#yemektarifleri, #evyemekleri, #kolaytarifler) tek biçimli; günün ana yemeği kendi adıyla; sonda sayfanın etiketi.
SABIT_ETIKETLER = ["#yemektarifleri", "#evyemekleri", "#kolaytarifler"]
MARKA_ETIKETI = "#akşamanevar"
ETIKET_EN_COK = 5
INSTAGRAMA_PAYLAS = True        # False: reel paylaşılmaz (kapatma anahtarı; Claude depodan değiştirir)
# Reel ana ızgaraya (Akış) girmez, yalnız Reels sekmesinde görünür (Rıdvan 23 Kas 12:52: "Reel ızgaraya girmesin
# (önerim): uygun"). Meta (IG User Media, share_to_feed): true → Akış ve Reels sekmesi; false → yalnız Reels sekmesi.
AKISA_PAYLAS = "false"
REEL_DENEME = 40 * 60           # geçici hatada en çok 40 dk dener
YUKLEME_SURESI = 300            # tek yükleme isteği en çok 5 dk
ISLEM_BEKLE = 15 * 60           # Instagram'ın videoyu işlemesi en çok 15 dk
KAPAK_ANI_MS = 1500             # kapak karesi: girişteki "Bugün ne yemek yapayım?" ekranı
# Yayın kipinde yalnız bugünün reel'i (paylas/paylas.py'deki eski gün korumasıyla aynı: iş kırmızı biter).
# Elle girilen eski tarih (ör. gönderisi çıkmış, reel'i çıkmamış bir gün) yayında reddedilir; prova serbest.
ESKI_GUN = "Yalnız bugünün reel'i paylaşılır; başka tarih yalnız prova içindir."


def cikti(ad, deger):
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a", encoding="utf-8") as f:
        f.write(f"{ad}={deger}\n")


def ozet(m):
    print(m)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(m + "\n")


def etiket_var(ad):
    r = subprocess.run(["git", "ls-remote", "--tags", "origin", f"refs/tags/{ad}"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise SystemExit("Etiketler okunamadı.")
    return bool(r.stdout.strip())


def gerek():
    olay = os.environ.get("OLAY", "")
    kip = os.environ.get("KIP", "") or "yayin"
    an = dt.datetime.now(IST)
    t = (os.environ.get("TARIH_GIRDI") or "").strip()
    if t and not re.match(r"^\d{4}-\d{2}-\d{2}$", t):
        raise SystemExit("Tarih YYYY-AA-GG olmalı.")
    tarih = t or an.date().isoformat()
    if kip == "yayin" and tarih != an.date().isoformat():
        raise P.Dur(ESKI_GUN)
    cikti("tarih", tarih)
    cikti("kip", kip)
    if olay == "workflow_run":
        if os.environ.get("SONUC") != "success":
            ozet("Paylaşım işi başarılı bitmedi; reel yok.")
            return cikti("gerek", "hayir")
        if not (OTO_ARALIK[0] <= an.time() < OTO_ARALIK[1]):
            ozet(f"Saat {an:%H:%M}: reel yalnız {OTO_ARALIK[0]:%H:%M}–{OTO_ARALIK[1]:%H:%M} arasında yapılır.")
            return cikti("gerek", "hayir")
    elif YASAK[0] <= an.time() < YASAK[1]:
        ozet("08:00–09:20 arasında elle reel denemesi yapılmaz (09:00 paylaşımı korunur).")
        return cikti("gerek", "hayir")
    if not etiket_var(f"paylasildi/{tarih}"):
        ozet(f"{tarih} gönderisi henüz paylaşılmadı; reel o gün paylaşımdan sonra yapılır.")
        return cikti("gerek", "hayir")
    if kip == "yayin" and etiket_var(f"reel/{tarih}"):
        ozet(f"{tarih} reel'i zaten paylaşılmış.")
        return cikti("gerek", "hayir")
    ozet(f"Reel hazırlanacak: {tarih} (kip: {kip}).")
    cikti("gerek", "evet")


def kucuk(metin):
    return metin.replace("I", "ı").replace("İ", "i").lower()


def yemek_etiketi(ad):
    ad = re.sub(r"\(.*?\)", "", ad)
    return "#" + "".join(h for h in kucuk(ad) if h.isalpha())


def etiketler(g):
    ana = next((y["ad"] for y in g["yemekler"] if y.get("tur") == "Ana yemek"), None)
    liste = list(SABIT_ETIKETLER)
    if ana and yemek_etiketi(ana) not in liste and len(yemek_etiketi(ana)) > 3:
        liste.append(yemek_etiketi(ana))
    liste.append(MARKA_ETIKETI)
    liste = list(dict.fromkeys(liste))[:ETIKET_EN_COK]
    return " ".join(liste)


def aciklama(g, tebrik=None):
    adlar = ", ".join(y["ad"] for y in g["yemekler"])
    # Ana söz (Rıdvan 17 Kas 15:38: "asıl odak noktamızı unutma. \"bugün ne yemek yapayım\""; 15:57 "olsun")
    # Özel günde tebrik en üstte (Rıdvan 17 Kas 16:15: "tabii ki uygun bir tebrik, kutlama veya günü önemini
    # belirten bir mesajı ile olacak bunlar."); söz aksama-bot/takvim/ozel-gunler.json'dan, videodakiyle aynı.
    satir = ([tebrik] if tebrik else []) + [f"Bugün ne yemek yapayım? Menü hazır: {adlar}.",
             "Her sabah 09:00'da yeni akşam yemeği menüsü için @aksama.ne.var'ı takip edin.",
             "Tarifler ve alışveriş listesi profildeki gönderide; kaydedin, akşam elinizin altında olsun.",
             "", YZ_SATIRI, TELIF_SATIRI, "", etiketler(g)]
    metin = "\n".join(satir)
    if len(re.findall(r"#\w+", metin)) > ETIKET_EN_COK or len(metin) > 2200:
        raise P.Dur("Reel açıklaması sınırı aşıyor (en çok 5 etiket, 2200 harf).")
    return metin


def etiket_yaz(tarih, mesaj):
    ad = f"reel/{tarih}"
    for i in range(3):
        a = subprocess.run(["git", "-c", "user.name=aksama-paylasim", "-c",
                            "user.email=aksama-paylasim@users.noreply.github.com",
                            "tag", "-f", "-a", ad, "-m", mesaj], capture_output=True, text=True)
        b = subprocess.run(["git", "push", "-f", "origin", f"refs/tags/{ad}"], capture_output=True, text=True, timeout=120)
        if a.returncode == 0 and b.returncode == 0:
            return True
        P.uyari(f"Reel etiketi yazılamadı (deneme {i + 1}): {(b.stderr or a.stderr).strip()[:200]}")
        P.uyu(10)
    return False


def ham_yukle(adres, veri, basliklar):
    """Tek HTTP isteği (denemede değiştirilir). Döner: Meta'nın JSON cevabı."""
    istek = urllib.request.Request(adres, data=veri, headers=basliklar, method="POST")
    try:
        with urllib.request.urlopen(istek, timeout=YUKLEME_SURESI) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            govde = json.loads(e.read().decode())
        except Exception:
            govde = {"error": {"message": f"HTTP {e.code}"}}
        raise P.GraphHatasi(e.code, govde)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise P.GraphHatasi(None, {"error": {"message": str(e)[:200]}}, ag=True)


def yukle(kap, uri, video):
    """Videoyu Meta'ya doğrudan yükler (resumable upload, tek parça; video açık bir adrese konmaz)."""
    veri = video.read_bytes()
    if not (uri or "").startswith("https://rupload.facebook.com/"):
        uri = f"{RUPLOAD}/{P.GRAPH.rstrip('/').rsplit('/', 1)[-1]}/{kap}"
    cevap = ham_yukle(uri, veri, {"Authorization": f"OAuth {P.TOKEN}", "offset": "0",
                                  "file_size": str(len(veri)), "Content-Type": "application/octet-stream"})
    if cevap.get("success") is False:
        raise P.GraphHatasi(None, {"error": {"message": f"yükleme kabul edilmedi: {str(cevap)[:150]}",
                                             "is_transient": True}})
    P.bilgi(f"Video Instagram'a yüklendi ({len(veri) // 1024} KB).")


def yan_bilgi(video, alan, uzunluk):
    """uretim/reel.py'nin videonun yanına yazdığı bilgi (muzik: parça adı, tebrik: özel günün satırı); yoksa None."""
    try:
        d = json.loads(video.with_suffix(".json").read_text(encoding="utf-8")).get(alan)
    except (OSError, ValueError, AttributeError):
        return None
    return d.strip()[:uzunluk] if isinstance(d, str) and d.strip() else None


def muzik_adi(video):
    return yan_bilgi(video, "muzik", 60)


def tebrik(video):
    return yan_bilgi(video, "tebrik", 300)


def bugun_reel(tarih, ilk):
    """Hesabın son paylaşımlarında bugünün reel'i var mı (aynı gün, aynı ilk satır)? Döner: medya kimliği ya da None."""
    r = P.graph("GET", f"{P.IG_ID}/media",
                {"fields": "id,caption,media_type,media_product_type,timestamp", "limit": "10"})
    for m in r.get("data", []):
        try:
            gun = dt.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(IST).date()
        except (KeyError, ValueError):
            continue
        reel = m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO"
        if gun == tarih and reel and P.ilk_satir(m.get("caption")) == ilk:
            return m["id"]
    return None


def kap_bekle(kap, son):
    bas = P.zaman()
    while True:
        s = P.dayanikli("reel kabı durumu", lambda: P.graph("GET", kap, {"fields": "status_code,status"}), son)
        kod = s.get("status_code")
        if kod == "FINISHED":
            return
        if kod in ("ERROR", "EXPIRED"):
            raise P.Dur(f"Instagram videoyu kabul etmedi ({kod}): {s.get('status', '')}")
        if P.zaman() - bas > ISLEM_BEKLE:
            raise P.Dur(f"Instagram videoyu {ISLEM_BEKLE // 60} dk içinde işlemedi.")
        P.uyu(15)


def yayinla(kap, tarih, ilk, son):
    """media_publish. Belirsiz hatada (gitmiş olabilir) Instagram'a bakmadan yeniden denemez."""
    deneme = 0
    while True:
        try:
            return P.graph("POST", f"{P.IG_ID}/media_publish", {"creation_id": kap}, zaman_asimi=120)
        except P.GraphHatasi as h:
            if not h.gecici():
                raise P.Dur(f"Reel paylaşılamadı: {h.kisa()}")
            P.uyari(f"Reel paylaşımı: geçici hata ({h.kisa()}); gidip gitmediğine bakılacak.")
            hata = h
        while True:
            b = P.bekleme_suresi(deneme, hata)
            if P.zaman() + b > son:
                raise P.Dur("Reel paylaşım süresi doldu; paylaşılmadı ya da belirsiz. Instagram'a elle bakılmalı.")
            P.uyu(b)
            deneme += 1
            try:
                var = bugun_reel(tarih, ilk)
                break
            except P.GraphHatasi as h2:
                P.uyari(f"Reel denetimi okunamadı: {h2.kisa()}")
        if var:
            return {"id": var, "_onceden": True}


def paylas():
    tarih_yazi, gun, video = sys.argv[2], pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
    kip = os.environ.get("KIP", "") or "yayin"
    if not INSTAGRAMA_PAYLAS:
        raise P.Bitti("Instagram'a reel paylaşımı kapalı (INSTAGRAMA_PAYLAS).")
    if not P.TOKEN:
        raise P.Dur("IG_TOKEN yok.")
    tarih = dt.date.fromisoformat(tarih_yazi)
    if kip == "yayin" and tarih != P.simdi().date():
        raise P.Dur(ESKI_GUN)
    g = json.loads((gun / "gun.json").read_text(encoding="utf-8"))
    metin = aciklama(g, tebrik(video))
    ilk = P.ilk_satir(metin)
    son = P.zaman() + REEL_DENEME
    if kip == "yayin":
        var = P.dayanikli("reel denetimi", lambda: bugun_reel(tarih, ilk), son)
        if var:
            etiket_yaz(tarih_yazi, f"media {var} (Instagram'da önceden paylaşılmış bulundu)")
            raise P.Bitti("Bugünün reel'i Instagram'da zaten var; yeniden paylaşılmadı.")
    if not video.is_file() or video.stat().st_size == 0:
        raise P.Dur(f"Video yok: {video}")
    prm = {"media_type": "REELS", "upload_type": "resumable", "caption": metin, "share_to_feed": AKISA_PAYLAS,
           "thumb_offset": str(KAPAK_ANI_MS)}
    ses = muzik_adi(video)
    if ses:
        prm["audio_name"] = ses
    if (os.environ.get("YZ_ETIKETI") or "hayir").strip().lower() == "evet":
        prm["is_ai_generated"] = "true"

    def kur_ve_yukle():
        # Yükleme yarıda kalırsa yeni kap kurulur (eskisi 24 saatte kendiliğinden silinir).
        r = P.graph("POST", f"{P.IG_ID}/media", prm)
        yukle(r["id"], r.get("uri"), video)
        return r["id"]

    kap = P.dayanikli("reel kabı ve yükleme", kur_ve_yukle, son)
    kap_bekle(kap, son)
    if kip != "yayin":
        ozet("Prova tamam: reel Instagram'a yüklendi ve hazır, **paylaşılmadı** (kap 24 saatte kendiliğinden silinir)"
             + (f"; ses adı: {ses}." if ses else "."))
        return
    sonuc = yayinla(kap, tarih, ilk, son)
    mid = sonuc["id"]
    try:
        m = P.graph("GET", mid, {"fields": "permalink,timestamp"})
    except P.GraphHatasi:
        m = {}
    yazildi = etiket_yaz(tarih_yazi, f"media {mid} {m.get('permalink', '')} {m.get('timestamp', '')}".strip())
    ozet(f"**Reel paylaşıldı** {P.simdi():%H:%M}: {m.get('permalink', mid)}"
         + (f" · müzik: {ses}" if ses else "")
         + (" (önceki denemede gitmiş)" if sonuc.get("_onceden") else ""))
    if not yazildi:
        raise P.Dur("Reel paylaşıldı ama kayıt etiketi yazılamadı.")


def calistir(adim):
    try:
        {"gerek": gerek, "paylas": paylas}[adim]()
    except P.Bitti as e:
        ozet(f"Yapılacak iş yok: {e}")
    except P.Dur as e:
        print(f"::error::{e}", flush=True)
        ozet(f"**Durdu:** {e}")
        sys.exit(1)


if __name__ == "__main__":
    calistir(sys.argv[1])
