"""Günlük reel videosu için yardımcı (iş akışı: .github/workflows/reel.yml).

Rıdvan 17 Kas 01:37: "Edits için müzik hariç bitmiş video yeterli. Çok uğraşamam"

  python3 paylas/reel.py gerek     bugünün gönderisi paylaşıldı mı, reel yapılmış mı, saat uygun mu
  python3 paylas/reel.py sayfa     _site/reel/index.html: video, indirme düğmesi, kopyalanacak açıklama
  python3 paylas/reel.py etiket    reel/<tarih> kayıt etiketini yazar

Açık depo: günlüğe menü ve açıklama yazılmaz. Video ve sayfa yalnız o günün gönderisi paylaşıldıktan
sonra yayımlanır (sıradaki günlerin içeriği önceden görünmez).
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import subprocess
import sys

IST = dt.timezone(dt.timedelta(hours=3))
OTO_ARALIK = (dt.time(8, 30), dt.time(19, 30))   # akşam 20:00 hazırlığının Pages'ini ezmesin
YASAK = (dt.time(8, 0), dt.time(9, 20))           # elle deneme yok (09:00 korunur)
SITE = pathlib.Path(os.environ.get("SITE_KLASORU", "_site"))
YZ_SATIRI = "Görseller temsilidir, yapay zekâ ile hazırlanmıştır."
TELIF_SATIRI = "Bu içerik Akşama Ne Var?™ sayfasına aittir. İzinsiz kopyalanamaz, başka sayfada yayımlanamaz."
ETIKETLER = "#akşamanevar #bugünnepişirsem #akşamyemeği #evyemekleri #menü"


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
        ozet(f"{tarih} reel'i zaten hazır.")
        return cikti("gerek", "hayir")
    ozet(f"Reel hazırlanacak: {tarih} (kip: {kip}).")
    cikti("gerek", "evet")


def aciklama(g):
    adlar = ", ".join(y["ad"] for y in g["yemekler"])
    satir = [f"Bugün akşama ne var? {adlar}.",
             "Tarifler ve alışveriş listesi profildeki gönderide. Kaydedin, akşam elinizin altında olsun.",
             "", YZ_SATIRI, TELIF_SATIRI, "", ETIKETLER]
    return "\n".join(satir)


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
<ol><li>Edits'i açın, indirdiğiniz videoyu seçin.</li><li>İsterseniz müzik ekleyin.</li>
<li>Instagram'da paylaşırken aşağıdaki açıklamayı yapıştırın.</li></ol>
<textarea id="t" readonly>{html.escape(metin)}</textarea>
<button onclick="navigator.clipboard.writeText(document.getElementById('t').value).then(()=>{{this.textContent='Kopyalandı'}})">2. Açıklamayı kopyala</button>
<p style="font-size:16px">Video akşam 20:00'ye kadar burada durur.</p>
</main></body></html>
""", encoding="utf-8")
    ozet("Sayfa hazır.")


def etiket():
    tarih = sys.argv[2]
    ad = f"reel/{tarih}"
    a = subprocess.run(["git", "-c", "user.name=aksama-paylasim", "-c",
                        "user.email=aksama-paylasim@users.noreply.github.com",
                        "tag", "-f", "-a", ad, "-m", f"Reel hazır: {tarih}"], capture_output=True, text=True)
    b = subprocess.run(["git", "push", "origin", f"refs/tags/{ad}"], capture_output=True, text=True, timeout=120)
    if a.returncode or b.returncode:
        raise SystemExit("Reel etiketi yazılamadı: " + (b.stderr or a.stderr)[:200])
    ozet(f"Kayıt: {ad}")


if __name__ == "__main__":
    {"gerek": gerek, "sayfa": sayfa, "etiket": etiket}[sys.argv[1]]()
