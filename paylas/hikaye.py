"""Öne çıkan halkaların hikâyeleri: depodaki hazır görseller Instagram'a hikâye (STORIES) olarak paylaşılır
(iş akışı: .github/workflows/hikaye.yml; elle başlatılır).

Rıdvan 17 Kas 19:11: "halka fikri hoşuma gitti. önerdiğin 2 halka uygun hemen yapalım. tabii resim de gerekir."
19:17: "instagram işini sen benim pc de şimdi yap"

  python3 paylas/hikaye.py <ad>        hikaye/<ad>/*.jpg dosya adı sırasıyla (kip: KIP=prova|yayin)

Instagram'ın masaüstü sitesi hikâye paylaşmaya izin vermiyor; hikâye Graph API ile paylaşılır, halka (öne çıkan)
sonra Instagram'da elle kurulur (API halka kuramaz). Görsel adresi açık depodaki dosyanın bu kayda ait ham adresi
(raw.githubusercontent.com); görseller herkese açık içerik olduğu için sakıncası yok.
Kilit: her hikâye için kayıt etiketi hikaye/<ad>/<dosya>; paylaşılmış hikâye yeniden paylaşılmaz (iş yarıda kesilip
yeniden çalıştırılırsa kaldığı yerden sürer).
"""
import datetime as dt
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paylas as P  # noqa: E402  (Graph API yardımcıları, süreler)

KOK = pathlib.Path(__file__).resolve().parent.parent
DEPO = os.environ.get("GITHUB_REPOSITORY", "ridvancoskun1975-cpu/aksama-medya")
IST = dt.timezone(dt.timedelta(hours=3))
YASAK = (dt.time(8, 0), dt.time(9, 20))     # sabah gönderisi ve reel korunur
SURE = 20 * 60                               # bütün iş en çok 20 dk dener
HAZIR_BEKLE = 5 * 60


def ozet(m):
    print(m)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(m + "\n")


def etiket_var(ad):
    r = subprocess.run(["git", "ls-remote", "--tags", "origin", f"refs/tags/{ad}"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise P.Dur("Etiketler okunamadı.")
    return bool(r.stdout.strip())


def etiket_yaz(ad, mesaj):
    for i in range(3):
        a = subprocess.run(["git", "-c", "user.name=aksama-paylasim", "-c",
                            "user.email=aksama-paylasim@users.noreply.github.com",
                            "tag", "-f", "-a", ad, "-m", mesaj], capture_output=True, text=True)
        b = subprocess.run(["git", "push", "-f", "origin", f"refs/tags/{ad}"], capture_output=True, text=True, timeout=120)
        if a.returncode == 0 and b.returncode == 0:
            return True
        P.uyari(f"Hikâye etiketi yazılamadı (deneme {i + 1}): {(b.stderr or a.stderr).strip()[:200]}")
        P.uyu(10)
    return False


def adres(ad, dosya, kayit):
    return f"https://raw.githubusercontent.com/{DEPO}/{kayit}/hikaye/{ad}/{dosya}"


def hazir_bekle(kap, son):
    bas = P.zaman()
    while True:
        s = P.dayanikli("hikâye kabı durumu", lambda: P.graph("GET", kap, {"fields": "status_code,status"}), son)
        kod = s.get("status_code")
        if kod in (None, "FINISHED"):
            return
        if kod in ("ERROR", "EXPIRED"):
            raise P.Dur(f"Instagram görseli kabul etmedi ({kod}): {s.get('status', '')}")
        if P.zaman() - bas > HAZIR_BEKLE:
            raise P.Dur("Instagram görseli 5 dk içinde işlemedi.")
        P.uyu(5)


def calistir(ad, simdi=None):
    kip = (os.environ.get("KIP") or "prova").strip()
    if kip not in ("prova", "yayin"):
        raise P.Dur(f"Bilinmeyen kip: {kip}")
    simdi = simdi or dt.datetime.now(IST)
    if YASAK[0] <= simdi.time() < YASAK[1]:
        raise P.Dur("08:00–09:20 arasında çalışmaz (sabah gönderisi ve reel korunur).")
    klasor = KOK / "hikaye" / ad
    dosyalar = sorted(p.name for p in klasor.glob("*.jpg"))
    if not dosyalar:
        raise P.Dur(f"hikaye/{ad} içinde görsel yok.")
    kayit = os.environ.get("GITHUB_SHA") or "main"
    son = P.zaman() + SURE
    paylasilan = atlanan = 0
    for d in dosyalar:
        etiket = f"hikaye/{ad}/{pathlib.Path(d).stem}"
        if etiket_var(etiket):
            atlanan += 1
            continue
        prm = {"media_type": "STORIES", "image_url": adres(ad, d, kayit)}
        kap = P.dayanikli("hikâye kabı", lambda prm=prm: P.graph("POST", f"{P.IG_ID}/media", prm)["id"], son)
        hazir_bekle(kap, son)
        if kip == "prova":
            ozet(f"Prova: {d} Instagram'a yüklendi, paylaşılmadı.")
            continue
        try:
            r = P.graph("POST", f"{P.IG_ID}/media_publish", {"creation_id": kap}, zaman_asimi=120)
        except P.GraphHatasi as h:
            # Belirsiz hatada yeniden denemez (iki kez gitmesin); kalanlar bir sonraki çalıştırmada.
            raise P.Dur(f"{d} paylaşılamadı ya da belirsiz ({h.kisa()}); Instagram'a bakıp iş yeniden başlatılmalı.")
        paylasilan += 1
        if not etiket_yaz(etiket, f"Hikâye paylaşıldı: {r.get('id')}"):
            raise P.Dur(f"{d} paylaşıldı ama etiketi yazılamadı; yeniden çalıştırmadan önce etiket elle yazılmalı.")
        ozet(f"Paylaşıldı: {d} ({r.get('id')})")
    ozet(f"Bitti: {paylasilan} hikâye paylaşıldı, {atlanan} hikâye önceden paylaşılmıştı ({kip}).")
    return paylasilan, atlanan


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    try:
        calistir(sys.argv[1])
    except P.Dur as e:
        ozet(f"DURDU: {e}")
        sys.exit(1)
