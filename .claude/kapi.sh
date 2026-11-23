#!/usr/bin/env bash
# Kapı: bir dal main'e alınmadan önce çalışır.
# Rıdvan 23 Kasım 2026 16:26: "ajanlar yalnız kendi dallarında çalışır, main'e yalnız yönetici alır.
# Sınamalar ve küçülme testi geçmeden kod main'e girmez."
#
# Kullanım (deponun kökünde, main checkout'unda):
#   bash .claude/kapi.sh <dal> [--silme-tamam] [--kuculme-tamam] [--onayli "<Rıdvan'ın sözü ve saati>"]
# Geçerse: git merge --ff-only <dal> && git push origin main   (pre-push kancası kapı işaretine bakar)
#
# Denetimler: 0) dal main'in üstünde mi  1) küçülme (silinen dosya, %30+ küçülen dosya, azalan/atlanan sınama,
# büyük toplu silme)  2) gizli bilgi (anahtar, belirteç)  3) korumalı dosya/satır (Rıdvan'ın onayı gerekir)
# 4) sözdizimi + deponun sınamaları (+ gerekiyorsa Android) dalın kendi kopyasında.
# Ayarlar main'deki .claude/kapi.conf'tan okunur (dal kapıyı kendisi gevşetemesin).
set -u
kok=$(git rev-parse --show-toplevel) || exit 2
cd "$kok" || exit 2
git config core.hooksPath .githooks 2>/dev/null || true

dal=""; silme=0; kuculme=0; onay=""; kurulum=0
while [ $# -gt 0 ]; do
  case "$1" in
    --silme-tamam) silme=1 ;;
    --kuculme-tamam) kuculme=1 ;;
    --onayli) shift; onay="${1:-}" ;;
    --kurulum) kurulum=1 ;;   # yalnız kapının ilk kurulumu: main'de henüz kapi.conf yokken
    -*) echo "bilinmeyen seçenek: $1"; exit 2 ;;
    *) dal="$1" ;;
  esac
  shift
done
[ -n "$dal" ] || { echo "kullanım: bash .claude/kapi.sh <dal> [--silme-tamam] [--kuculme-tamam] [--onayli \"...\"]"; exit 2; }
[ "$dal" != main ] || { echo "main'in kendisi kapıdan geçirilmez; bir dal ver."; exit 2; }
git rev-parse -q --verify "$dal^{commit}" >/dev/null || { echo "dal yok: $dal"; exit 2; }

# Ayarlar: main'deki kapi.conf (kurulumda dalınki)
SINAMA_KOMUTU=""; ANDROID_YOLLARI=""; ANDROID_KOMUTU=""; KORUMALI_DOSYA=(); KORUMALI_SATIR=()
if conf=$(git show "main:.claude/kapi.conf" 2>/dev/null); then :
elif [ $kurulum -eq 1 ] && conf=$(git show "$dal:.claude/kapi.conf" 2>/dev/null); then echo "! kurulum: ayarlar dalın kapi.conf'undan"
else echo "main'de .claude/kapi.conf yok"; exit 2; fi
eval "$conf"

hata=0
kotu() { echo "  ✗ $*"; hata=1; }
iyi() { echo "  ✓ $*"; }

echo "Kapı: $dal → main"
echo "0) Dal ve main"
git fetch -q origin main 2>/dev/null || echo "  ! origin'e ulaşılamadı; yerel main'e göre denetleniyor"
if git rev-parse -q --verify origin/main >/dev/null && ! git merge-base --is-ancestor origin/main main; then
  kotu "yerel main origin/main'in gerisinde: main'de 'git pull --ff-only' yap"
fi
if ! git merge-base --is-ancestor main "$dal"; then
  kotu "$dal main'in üstünde değil: dalı main'e göre güncelle (git -C <dal klasörü> rebase main) ve kapıyı yeniden çalıştır"
fi
if [ $hata -ne 0 ]; then echo "KAPI KAPALI"; exit 1; fi
sayi=$(git rev-list --count "main..$dal")
[ "$sayi" -gt 0 ] || { echo "  dalda main'de olmayan commit yok"; exit 1; }
iyi "$sayi commit, main'in üstünde"

degisen=$(git diff --name-only -M main "$dal")

echo "1) Küçülme denetimi"
while IFS=$'\t' read -r durum yol _; do
  [ "$durum" = D ] || continue
  if [ $silme -eq 1 ]; then iyi "silindi (yönetici onayladı): $yol"
  else kotu "dosya silinmiş: $yol  (bilerek silindiyse yönetici bakıp --silme-tamam verir)"; fi
done < <(git diff --name-status -M main "$dal")
top_ekl=0; top_sil=0
while IFS=$'\t' read -r ekl sil yol; do
  [ "$ekl" = "-" ] && continue
  top_ekl=$((top_ekl + ekl)); top_sil=$((top_sil + sil))
  git cat-file -e "main:$yol" 2>/dev/null || continue
  git cat-file -e "$dal:$yol" 2>/dev/null || continue
  eski=$(git show "main:$yol" | wc -l); yeni=$(git show "$dal:$yol" | wc -l)
  if [ "$eski" -ge 40 ] && [ $((yeni * 10)) -lt $((eski * 7)) ]; then
    if [ $kuculme -eq 1 ]; then iyi "küçüldü (yönetici onayladı): $yol $eski → $yeni satır"
    else kotu "dosya %30'dan çok küçülmüş: $yol $eski → $yeni satır (kesik içerik olabilir)"; fi
  fi
done < <(git diff --numstat --no-renames main "$dal")
if [ $top_sil -gt 400 ] && [ $top_sil -gt $((top_ekl * 2)) ] && [ $kuculme -eq 0 ]; then
  kotu "toplu silme: -$top_sil / +$top_ekl satır"
fi
test_kalip='(^|/)(test_[^/]*|[^/]*_test\.[a-z]+|[^/]*Test\.kt|[^/]*\.test\.js)$|/test/'
sinama_say() { grep -cE '^\s*(def test|@Test|(it|test)\()' 2>/dev/null || true; }
for yol in $degisen; do
  echo "$yol" | grep -qE "$test_kalip" || continue
  git cat-file -e "main:$yol" 2>/dev/null || continue
  e=$(git show "main:$yol" | sinama_say); y=$(git show "$dal:$yol" 2>/dev/null | sinama_say)
  if [ "${y:-0}" -lt "${e:-0}" ] && [ $kuculme -eq 0 ]; then kotu "sınama sayısı azalmış: $yol $e → ${y:-0}"; fi
done
test_dosyalari=$(echo "$degisen" | grep -E "$test_kalip" || true)
atlanan=0
if [ -n "$test_dosyalari" ]; then
  # shellcheck disable=SC2086
  atlanan=$(git diff -U0 main "$dal" -- $test_dosyalari | grep -E '^\+' | grep -vE '^\+\+\+' | grep -cE '@Ignore|unittest\.skip|\.skip\(|@pytest\.mark\.skip|xit\(' || true)
fi
[ "$atlanan" -eq 0 ] || { [ $kuculme -eq 1 ] && iyi "atlanan sınama eklendi (yönetici onayladı)" || kotu "atlanan (skip) sınama eklenmiş: $atlanan yer"; }
[ $hata -eq 0 ] && iyi "küçülme yok (+$top_ekl / -$top_sil satır)"

echo "2) Gizli bilgi"
gizli='-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{24,}|xox[baprs]-[A-Za-z0-9-]{10,}|EAA[A-Za-z0-9]{60,}|"private_key"[[:space:]]*:'
bulunan=$(git diff -U0 main "$dal" | grep -E '^\+' | grep -vE '^\+\+\+' | grep -cE -- "$gizli" || true)
yeni_env=$(git diff --name-status main "$dal" | awk -F'\t' '$1=="A"{print $2}' | grep -E '(^|/)\.env(\.|$)' || true)
if [ "$bulunan" -gt 0 ]; then kotu "eklenen satırlarda anahtar/belirteç benzeri $bulunan yer var (anahtar depoya yazılmaz)"; fi
if [ -n "$yeni_env" ]; then kotu ".env dosyası eklenmiş: $yeni_env"; fi
[ "$bulunan" -eq 0 ] && [ -z "$yeni_env" ] && iyi "gizli bilgi yok"

echo "3) Korumalı dosya ve satırlar"
korumali=""
for yol in $degisen; do
  for kalip in "${KORUMALI_DOSYA[@]}"; do
    # shellcheck disable=SC2053
    [[ "$yol" == $kalip ]] && korumali="$korumali\n    dosya: $yol"
  done
done
for desen in "${KORUMALI_SATIR[@]}"; do
  s=$(git diff -U0 main "$dal" | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -E -- "$desen" | head -3)
  [ -n "$s" ] && korumali="$korumali\n    satır ($desen):\n$(echo "$s" | sed 's/^/      /')"
done
if [ -n "$korumali" ]; then
  if [ -n "$onay" ]; then iyi "korumalı değişiklik, Rıdvan'ın onayıyla: \"$onay\""; echo -e "$korumali"
  else kotu "korumalı değişiklik: Rıdvan'ın onayı gerekir (--onayli \"<sözü ve saati>\")"; echo -e "$korumali"; fi
else iyi "korumalı değişiklik yok"; fi

echo "4) Sözdizimi ve sınamalar (dalın kendi kopyasında)"
gecici=$(mktemp -d /tmp/kapi.XXXXXX)
git worktree add -q --detach "$gecici" "$dal" || { kotu "geçici kopya açılamadı"; gecici=""; }
if [ -n "$gecici" ]; then
  (
    cd "$gecici" || exit 1
    shata=0
    for yol in $degisen; do
      [ -f "$yol" ] || continue
      case "$yol" in
        *.py) python3 -m py_compile "$yol" 2>/dev/null || { echo "  ✗ sözdizimi: $yol"; shata=1; } ;;
        *.js) node --check "$yol" 2>/dev/null || { echo "  ✗ sözdizimi: $yol"; shata=1; } ;;
        *.gs) cp "$yol" /tmp/kapi-gs.js && node --check /tmp/kapi-gs.js 2>/dev/null || { echo "  ✗ sözdizimi: $yol"; shata=1; } ;;
        *.json) python3 -m json.tool "$yol" >/dev/null 2>&1 || { echo "  ✗ JSON bozuk: $yol"; shata=1; } ;;
        *.yml|*.yaml) python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1]))' "$yol" 2>/dev/null || { echo "  ✗ YAML bozuk: $yol"; shata=1; } ;;
        *.sh) bash -n "$yol" 2>/dev/null || { echo "  ✗ sözdizimi: $yol"; shata=1; } ;;
      esac
    done
    [ $shata -eq 0 ] && echo "  ✓ sözdizimi"
    if ! echo "$degisen" | grep -vqE '\.md$|^docs/|^claude/'; then
      echo "  ✓ yalnız belge değişmiş; sınamalar atlandı"; exit $shata
    fi
    if [ -n "$SINAMA_KOMUTU" ]; then
      if bash -c "$SINAMA_KOMUTU" > /tmp/kapi-sinama.log 2>&1; then echo "  ✓ sınamalar geçti"
      else echo "  ✗ sınamalar kaldı (son satırlar):"; tail -15 /tmp/kapi-sinama.log | sed 's/^/      /'; shata=1; fi
    else echo "  ! bu depoda sınama komutu tanımlı değil"; fi
    if [ -n "$ANDROID_YOLLARI" ] && echo "$degisen" | grep -qE "$ANDROID_YOLLARI"; then
      bash -c "$ANDROID_KOMUTU" > /tmp/kapi-android.log 2>&1; r=$?
      if [ $r -eq 0 ]; then echo "  ✓ Android sınamaları ve lint geçti"
      elif [ $r -eq 3 ]; then echo "  ✗ Android derlemesi denenemedi (SDK yok); uygulama kodu denenmeden main'e girmez"; shata=1
      else echo "  ✗ Android sınamaları kaldı (son satırlar):"; tail -15 /tmp/kapi-android.log | sed 's/^/      /'; shata=1; fi
    fi
    exit $shata
  ) || hata=1
  git worktree remove --force "$gecici" 2>/dev/null || rm -rf "$gecici"
fi

if [ $hata -ne 0 ]; then echo "KAPI KAPALI: $dal main'e alınamaz."; exit 1; fi
isaret="$(git rev-parse --git-common-dir)/kapi-gecti"
mkdir -p "$isaret"
sha=$(git rev-parse "$dal")
{ date -Is; echo "dal: $dal"; [ -n "$onay" ] && echo "onay: $onay"; } > "$isaret/$sha"
echo "KAPI AÇIK: $dal ($sha)"
echo "Birleştir: git merge --ff-only $dal && git push origin main"
[ -n "$onay" ] && echo "Commit iletisine Rıdvan'ın onayını yaz: $onay"
exit 0
