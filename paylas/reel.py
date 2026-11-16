"""Günlük reel: video üretilir, Pages'e konur ve Instagram'a kendiliğinden paylaşılır (iş akışı: .github/workflows/reel.yml).

Rıdvan 17 Kas 01:37: "Edits için müzik hariç bitmiş video yeterli. Çok uğraşamam"
Rıdvan 17 Kas 01:54: "Ben uğraşmak istemiyorum, sen yap." · "Edits iptal"

  python3 paylas/reel.py gerek                          bugünün gönderisi paylaşıldı mı, reel paylaşılmış mı, saat uygun mu
  python3 paylas/reel.py sayfa <gün klasörü>            _site/reel/index.html (video ve açıklama; yedek)
  python3 paylas/reel.py paylas <tarih> <gün> <video>   Instagram'a reel (kip prova: kap kurulur, paylaşılmaz)

Reel yalnız o günün onaylı gönderisi paylaşıldıktan sonra (etiket paylasildi/<tarih>) ve aynı menüden üretilir.
Kilitler: kayıt etiketi reel/<tarih> ve Instagram'daki son paylaşımlar (aynı gün, aynı ilk satır) — aynı reel iki kez gitmez.
Açık depo: günlüğe menü ve açıklama yazılmaz. Müzik Graph API ile eklenemez; video müziksiz gider.
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402  (Graph API yardımcıları, kilitler, süreler)

IST = dt.timezone(dt.timedelta(hours=3))
OTO_ARALIK = (dt.time(8, 30), dt.time(19, 30))   # akşam 20:00 hazırlığının Pages'ini ezmesin
YASAK = (dt.time(8, 0), dt.time(9, 20))           # elle deneme yok (09:00 korunur)
SITE = pathlib.Path(os.environ.get("SITE_KLASORU", "_site"))
YZ_SATIRI = "Görseller temsilidir, yapay zekâ ile hazırlanmıştır."
TELIF_SATIRI = "Bu içerik Akşama Ne Var?™ sayfasına aittir. İzinsiz kopyalanamaz, başka sayfada yayımlanamaz."
# Hashtag (Rıdvan 17 Kas 01:57: "Takipçi kazanma odaklı. Hashtagler dikkat!!"): Instagram en çok 5 izin veriyor
# (Aralık 2025). Konuya uyan, aranan etiketler; genel ya da ilgisiz etiket yok. Türkçe harfsiz yazılanlar
# (#yemektarifleri, #evyemekleri, #kolaytarifler) tek biçimli; günün ana yemeği kendi adıyla; sonda sayfanın etiketi.
SABIT_ETIKETLER = ["#yemektarifleri", "#evyemekleri", "#kolaytarifler"]
MARKA_ETIKETI = "#akşamanevar"
ETIKET_EN_COK = 5
INSTAGRAMA_PAYLAS = True        # False: video yalnız Pages'e konur (kapatma anahtarı; Claude depodan değiştirir)
REEL_DENEME = 40 * 60           # geçici hatada en çok 40 dk dener
VIDEO_BEKLE = 15 * 60           # video en çok 15 dk içinde Pages'te görünmeli
ISLEM_BEKLE = 15 * 60           # Instagram'ın videoyu işlemesi en çok 15 dk
KAPAK_ANI_MS = 1500             # kapak karesi: girişteki "Bugün akşama ne pişirsem?" ekranı


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


def aciklama(g):
    adlar = ", ".join(y["ad"] for y in g["yemekler"])
    satir = [f"Bugün akşama ne pişirsem? Menü hazır: {adlar}.",
             "Her sabah 09:00'da yeni akşam yemeği menüsü için @aksama.ne.var'ı takip edin.",
             "Tarifler ve alışveriş listesi profildeki gönderide; kaydedin, akşam elinizin altında olsun.",
             "", YZ_SATIRI, TELIF_SATIRI, "", etiketler(g)]
    metin = "\n".join(satir)
    if len(re.findall(r"#\w+", metin)) > ETIKET_EN_COK or len(metin) > 2200:
        raise P.Dur("Reel açıklaması sınırı aşıyor (en çok 5 etiket, 2200 harf).")
    return metin


def sayfa():
    gun = pathlib.Path(sys.argv[2])
    g = json.loads((gun / "gun.json").read_text(encoding="utf-8"))
    metin = aciklama(g)
    (SITE / "reel").mkdir(parents=True, exist_ok=True)
    (SITE / "reel" / "index.html").write_text(f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Bugünün reel'i · Akşama Ne Var?</title>
<style>
body{{margin:0;background:#FBF4E6;color:#3F322A;font:18px/1.45 system-ui,sans-serif}}
main{{max-width:520px;margin:0 auto;padding:18px}}
h1{{font-size:24px;color:#C8463A;margin:4px 0 2px}} p{{margin:8px 0}}
video{{width:100%;border-radius:16px;background:#000}}
a.dugme,button{{display:block;width:100%;box-sizing:border-box;text-align:center;margin:12px 0;padding:16px;border:0;
  border-radius:14px;background:#C8463A;color:#fff;font:700 20px system-ui,sans-serif;text-decoration:none}}
button{{background:#6E7D3E}}
textarea{{width:100%;box-sizing:border-box;height:190px;font:16px/1.4 system-ui,sans-serif;border-radius:12px;padding:10px}}
ol{{padding-left:22px}} li{{margin:6px 0}}
</style></head><body><main>
<h1>Bugünün reel'i</h1><p>{html.escape(g['tarih_yazi'])}</p>
<video src="../reel.mp4" controls playsinline preload="metadata"></video>
<a class="dugme" href="../reel.mp4" download="aksama-reel-{gun.name}.mp4">1. Videoyu indir</a>
<p>Bu video Instagram'a kendiliğinden paylaşılır; sizin bir şey yapmanız gerekmez. Sayfa yalnız yedektir.</p>
<textarea id="t" readonly>{html.escape(metin)}</textarea>
<button onclick="navigator.clipboard.writeText(document.getElementById('t').value).then(()=>{{this.textContent='Kopyalandı'}})">2. Açıklamayı kopyala</button>
<p style="font-size:16px">Video akşam 20:00'ye kadar burada durur.</p>
</main></body></html>
""", encoding="utf-8")
    ozet("Sayfa hazır.")


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


def boyut_oku(adres):
    """Pages'teki videonun boyutu (video/mp4 değilse ya da açılmıyorsa None)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{adres}?v={secrets.token_hex(4)}",
                                    headers={"User-Agent": "aksama-medya-reel"}), timeout=60) as r:
            if r.status != 200 or not r.headers.get("Content-Type", "").startswith("video/mp4"):
                return None
            return len(r.read())
    except Exception:
        return None


def video_yayinda(adres, boyut):
    bas = P.zaman()
    while boyut_oku(adres) != boyut:
        if P.zaman() - bas > VIDEO_BEKLE:
            raise P.Dur(f"Video {VIDEO_BEKLE // 60} dk içinde Pages'te görünmedi.")
        P.uyu(15)
    P.bilgi("Video Pages'te.")


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
        raise P.Bitti("Instagram'a reel paylaşımı kapalı (INSTAGRAMA_PAYLAS); video yalnız Pages'te.")
    if not P.TOKEN:
        raise P.Dur("IG_TOKEN yok.")
    tarih = dt.date.fromisoformat(tarih_yazi)
    g = json.loads((gun / "gun.json").read_text(encoding="utf-8"))
    metin = aciklama(g)
    ilk = P.ilk_satir(metin)
    son = P.zaman() + REEL_DENEME
    if kip == "yayin":
        var = P.dayanikli("reel denetimi", lambda: bugun_reel(tarih, ilk), son)
        if var:
            etiket_yaz(tarih_yazi, f"media {var} (Instagram'da önceden paylaşılmış bulundu)")
            raise P.Bitti("Bugünün reel'i Instagram'da zaten var; yeniden paylaşılmadı.")
    taban = (os.environ.get("SAYFA_ADRESI") or "").rstrip("/")
    if not taban:
        raise P.Dur("Pages adresi yok (deploy-pages çıktısı).")
    adres = f"{taban}/reel.mp4"
    video_yayinda(adres, video.stat().st_size)
    prm = {"media_type": "REELS", "video_url": adres, "caption": metin, "share_to_feed": "true",
           "thumb_offset": str(KAPAK_ANI_MS)}
    if (os.environ.get("YZ_ETIKETI") or "hayir").strip().lower() == "evet":
        prm["is_ai_generated"] = "true"
    kap = P.dayanikli("reel kabı", lambda: P.graph("POST", f"{P.IG_ID}/media", prm)["id"], son)
    kap_bekle(kap, son)
    if kip != "yayin":
        ozet("Prova tamam: reel Instagram'da hazır, **paylaşılmadı** (kap 24 saatte kendiliğinden silinir).")
        return
    sonuc = yayinla(kap, tarih, ilk, son)
    mid = sonuc["id"]
    try:
        m = P.graph("GET", mid, {"fields": "permalink,timestamp"})
    except P.GraphHatasi:
        m = {}
    yazildi = etiket_yaz(tarih_yazi, f"media {mid} {m.get('permalink', '')} {m.get('timestamp', '')}".strip())
    ozet(f"**Reel paylaşıldı** {P.simdi():%H:%M}: {m.get('permalink', mid)}"
         + (" (önceki denemede gitmiş)" if sonuc.get("_onceden") else ""))
    if not yazildi:
        raise P.Dur("Reel paylaşıldı ama kayıt etiketi yazılamadı.")


def calistir(adim):
    try:
        {"gerek": gerek, "sayfa": sayfa, "paylas": paylas}[adim]()
    except P.Bitti as e:
        ozet(f"Yapılacak iş yok: {e}")
    except P.Dur as e:
        print(f"::error::{e}", flush=True)
        ozet(f"**Durdu:** {e}")
        sys.exit(1)


if __name__ == "__main__":
    calistir(sys.argv[1])
