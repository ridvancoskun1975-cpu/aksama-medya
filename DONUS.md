# Otomatiğe dönüş: kontrol listesi

> **Dönüş yalnız Rıdvan'ın açık sözüyle başlar.** GEÇİCİ POLİTİKA (Rıdvan 23 Kas 2026) sürdükçe bu listenin hiçbir adımı yapılmaz: iş akışı açılmaz, kilit kaldırılmaz, kontrol ya da prova başlatılmaz. Meta kısıtlaması kalkınca Rıdvan "otomatiğe dön" der ve son elle paylaşım gününü (aşağıda **D**) söyler. Aşama 3 (reel) ve aşama 4 (hikâye) için ayrıca söz gerekir.
>
> Bu liste hazırlıktır (Rıdvan 25 Kas 23:05 "2 ok"). Ana plan `claude/yol-haritasi.md` "Geçici politika"dır; çelişirse o ve Rıdvan'ın sözü geçer. Yönetici her aşamanın sonunda Rıdvan'a rapor verir.

**Kim yapar:** **Rıdvan** = yalnız Rıdvan yapar · **Yönetici + söz** = yönetici yapar, Rıdvan'ın açık sözü gerekir · **Yönetici** = yönetici kendisi yapar (Instagram'a gitmez).

## Dönüş gününde elle paylaşım kuralı

- **D sabahı** (son elle gün): Rıdvan gönderiyi elle **kaydırmalı olarak** paylaşır ve **açıklamanın ilk satırını değiştirmez**. Aynı gün kazara başlayan bir iş (geciken yedek saat, nöbetçi) gönderiyi Instagram'da bu ilk satırdan tanır ve yeniden paylaşmaz. İlk satır farklıysa ya da tek resim paylaşıldıysa tanımaz ve gönderi **ikinci kez çıkar**. Rıdvan o gün reel'i elle paylaşırsa yöneticiye söyler.
- **D+1 ve sonrası**: elle paylaşım yok. 09:00 gönderisi çıkmazsa Rıdvan elle paylaşabilir ama ilk satırı aynen kullanır, böylece sonraki denemeler gönderiyi tanıyıp durur. Bunun yerine yönetici önce `PAYLASIM_KIPI=kontrol` da yapabilir.
- Otomatik gönderi 09:00'da çıktıktan sonra elle paylaşılan gönderiyi kod önleyemez, çünkü kod paylaşmadan önce bakar. Rıdvan 09:00–09:10 arasında Instagram'a bakmadan elle paylaşmaz.
- Reel aşamasının ilk günü (aşama 3) Rıdvan reel'i elle paylaşmaz. Elle reel'in ilk satırı otomatik reel'inkiyle aynı değilse ikinci reel çıkar.

## Aşama 0: hazırlık (bugün yapılabilir, Instagram'a gitmez)

1. `ajan/donus-hazirlik` dalı kapıdan geçer ve main'e alınır (`bash .claude/kapi.sh ajan/donus-hazirlik`). **Yönetici**
2. Google "Akşama dış tetik" betiğinde `ELLE_DONEM` anahtarının ne yaptığı ve reel tetiğinin hangi `kip` girdisini gönderdiği okunur. Bu bilgi bu depoda yazmıyor (belirsiz). **Yönetici** (Rıdvan'ın hesabında yalnız okuma)

## Aşama 1: D günü (Rıdvan sabah son kez elle paylaşır)

Sıra önemlidir: **önce kip, sonra kilit, sonra iş akışı.** Şu anki `PAYLASIM_KIPI` değeri bilinmiyor; `yayin` iken iş akışı açılırsa 12:05 yedeği D'yi paylaşmaya kalkar.

1. **`PAYLASIM_KIPI` denetimi:** `gh variable list`; değer `kontrol` değilse `gh variable set PAYLASIM_KIPI --body kontrol`. **Yönetici + söz**
2. **Kilit satırı, yalnız `paylas.yml`:** işin `if:` satırındaki `false && ` kısmı silinir; geriye `github.repository == 'ridvancoskun1975-cpu/aksama-medya'` koşulu kalır. Üstündeki GEÇİCİ POLİTİKA yorumu da güncellenir. `reel.yml` ve `hikaye.yml` kilitli kalır. İş `yonetici/donus-paylasim` dalında yapılır, sonra `bash .claude/kapi.sh yonetici/donus-paylasim --onayli "<Rıdvan'ın sözü ve saati>"`, `git merge --ff-only`, `git push origin main`. **Yönetici + söz**
3. **İş akışını aç:** 09:20'den sonra `gh workflow enable paylas.yml` (yalnız Paylaşım). Kip `kontrol` olduğu için 12:05 yedeği Instagram'a yazmaz, yalnız okur. Not: herkese açık depoda 60 gün etkinlik olmazsa GitHub zamanlanmış işleri kendiliğinden kapatır; bu adım onları da açar. **Yönetici + söz**
4. **Kontrol:** 09:20'den sonra `gh workflow run paylas.yml -f kip=kontrol`. 08:00–09:20 arasında elle kontrol ve prova yapılmaz. Günlükte şunlara bakılır: hesap `aksama.ne.var`, anahtarın türü, süresi, veri erişimi ve izinleri, paylaşım payı, stok, D+1 gün klasörü ve onayı (kontrol bugünün klasörüne bakar; D+1 için `-f tarih=<D+1>` ile ikinci bir kontrol yapılır). Kırmızıysa durulur. **Yönetici + söz**
5. **Prova, D+1 tarihiyle:** `gh workflow run paylas.yml -f kip=prova -f tarih=<D+1>`. **Tarihsiz prova yapılmaz:** tarihsiz prova D'nin kabını kurar ve aynı gün yayına geçilirse sonraki tetik o kabı hemen paylaşır. Bakılacaklar: Pages'e çıktı mı, kapak videosu, kaplar hazır mı, sonuçta "paylaşılmadı" yazıyor mu. **Yönetici + söz**
6. **Yayına geçiş, D akşamı 18:00–19:45:** Google'ın son nöbetçisi (17:40) bitmiş, 20:00 akşam hazırlığı başlamamış olur.
   - a. Sırada ya da çalışmakta Paylaşım işi olmamalı: `gh run list --workflow paylas.yml --status queued` ve `--status in_progress`. Geciken bir yedek saat geçişten sonra başlarsa D'yi paylaşmaya kalkar; elle gönderiyi ancak ilk satırı aynıysa tanır. **Yönetici**
   - b. `gh variable set PAYLASIM_KIPI --body yayin`. Yazım tam `yayin` olmalı. `yayın` (ı) ya da başka bir yazım kontrole düşer: iş yeşil biter ama paylaşmaz. **Yönetici + söz**
   - c. Google dış tetik: `ELLE_DONEM = false`. **Rıdvan** (ya da onun sözüyle yönetici)
7. **D 20:00:** Google akşam hazırlığı D+1 gönderisini Instagram'a yükler, paylaşmaz. Yeşil bitmesi gerekir. Kırmızı biterse geri alınır (aşağıda) ve D+1 sabahı Rıdvan elle paylaşır. **Yönetici** izler, Rıdvan'a bildirir.

## Aşama 2: D+1, ilk otomatik gün

1. Rıdvan elle paylaşmaz. **Rıdvan**
2. 09:00 gönderisi Instagram'da görünür ve `paylasildi/<D+1>` etiketi yazılır. 09:05 ve 12:05 yedekleri ile nöbetçi "zaten paylaşılmış" diyerek çıkar. **Yönetici** izler ve rapor verir.
3. Reel ve ek gönderi kapalı kalır. Reel işi kapalıdır ve `false && ` kilidi duruyor; Google'ın reel tetiği bir şey yapmaz (kapalı iş akışını tetiklemenin Google tarafında hata verip vermediği belirsiz). Ek gönderi reel işinin bir adımı olduğu için o da çalışmaz. Reel istenirse bu aşamada elle paylaşılır. **Rıdvan**

## Aşama 3: reel (öneri: günlük gönderi en az 3 gün sorunsuz çıktıktan sonra; Rıdvan'ın ayrı sözüyle)

1. **Ek gönderi denetimi:** `python3 paylas/ek.py denetle` ve `git ls-remote --tags origin 'refs/tags/ek/*'` çalıştırılır. Yayın kipinde yalnız `ek.json`'daki gün paylaşılır: tarihi geçmiş, etiketsiz ek gönderi "süresi geçti" diye atlanır, günlüğe uyarı (`::warning::`) yazılır ve iş yeşil biter (açık kapandı, 25 Kas). Böyle bir ek gönderi istenirse `ek.json`'daki tarih reel'in açık olduğu bir güne çekilir; onay özeti kareler ve açıklamadır, tarih onayı bozmaz. Ek gönderi kendi gününde bir hatayla çıkmazsa ertesi gün yeniden denenmez; tarih yine elle çekilir. 25 Kas'ta tek ek gönderi vardı (`ek/2026-11-tanitim`, 19 Kas) ve etiketliydi. **Yönetici**
2. `reel.yml` kilit satırı kaldırılır (aşama 1, adım 2'deki yolla, kapı `--onayli`), ardından `gh workflow enable reel.yml`. Kilit satırı kaldırılırken aynı dosyadaki "Ek gönderi" adımının yorumu da güncellenir: orada hâlâ eski kural (`ek.json`'daki günden başlayarak) yazıyor; yeni kural yalnız o gün, tarihi geçerse "süresi geçti" (25 Kas; korumalı dosya olduğu için o gün değiştirilmedi). **Yönetici + söz**
3. **Reel provası:** günün gönderisi çıktıktan sonra ve 09:20'den sonra `gh workflow run reel.yml -f kip=prova`. Aynı işteki ek gönderi adımı da prova kipinde çalışır: her ek gönderi için kap kurar, paylaşmaz. Bakılacaklar: video, ses adı, `share_to_feed=false` (reel ana ızgaraya girmez). **Yönetici + söz**
4. **Reel kipi:** reel işi `PAYLASIM_KIPI`'ye bakmaz. Yayına çıkması yalnız iki şeye bağlıdır: tetiğin `kip` girdisi (iş akışında varsayılan `prova`) ve `paylasildi/<bugün>` etiketi. Google'ın `kip=yayin` gönderdiği doğrulanır (aşama 0, adım 2). Yayın kipinde yalnız bugünün reel'i gider: elle eski (ya da ileri) bir tarih girilirse iş kırmızı biter, video üretilmez, Instagram'a istek gitmez (paylaşım işindeki eski gün korumasıyla aynı; açık kapandı, 25 Kas). Eski tarih yalnız provada kullanılır. **Yönetici**
5. İlk reel günü Rıdvan reel'i elle paylaşmaz. **Rıdvan**

## Aşama 4: hikâye (isteğe bağlı; yalnız Rıdvan bir halka isterse)

1. `hikaye.yml` kilidi kaldırılır ve iş akışı açılır (aşama 1, adım 2 ve 3'teki yolla). **Yönetici + söz**
2. `gh workflow run hikaye.yml -f ad=<klasör> -f kip=prova`, ardından `kip=yayin`. Hikâye günlük değildir; yalnız adı verilen klasör gider ve etiketli dosyalar yeniden gitmez. 25 Kas'ta etiketsiz klasör yalnız `hikaye/2026-11-nasil-sade` (2 dosya). 08:00–09:20 arasında çalışmaz. **Yönetici + söz**

## Geri alma (her aşamada)

1. **Hemen, commit gerekmez:**
   - `gh variable set PAYLASIM_KIPI --body kontrol`. Çalışmakta olan iş kipi başlarken aldığı için 09:00'ı bekleyen iş iptal edilir: `gh run list --workflow paylas.yml --status in_progress`, sonra `gh run cancel <no>` (henüz paylaşmamıştır).
   - `gh workflow disable reel.yml`. Reel `PAYLASIM_KIPI`'ye bakmaz; o günün etiketi varsa yine paylaşır.
   - `gh workflow disable paylas.yml` ve `gh workflow disable hikaye.yml`.
   - Google dış tetik: `ELLE_DONEM = true`.

   **Yönetici + söz.** Öneri (Rıdvan onaylamalı): çift paylaşım ya da Meta uyarısı görülürse yönetici önce durdurur, hemen bildirir.
2. Kilit geri gelir: üç işin `if:` satırının başına `false && ` yeniden eklenir (kapı `--onayli`). **Yönetici + söz**
3. Paylaşım yeniden telefondan elle yapılır. **Rıdvan**

## Anahtar ve izin: dönüşte bakılacaklar

Kodun kullandığı uçlar (Graph API `v26.0`, anahtar `IG_TOKEN`). Sahte sunucu sınamaları bu listeyi doğrular:

| Uç | Ne için | Kim kullanır |
|---|---|---|
| `GET /{IG_ID}?fields=id,username` | hesap kilidi (`aksama.ne.var`) | paylaşım |
| `GET /debug_token` | geçerlilik, tür, süre, veri erişim süresi, izinler | paylaşım |
| `GET /{IG_ID}/content_publishing_limit` | 24 saatlik pay | paylaşım |
| `GET /{IG_ID}/media` (limit 10 ya da 25) | kilit 2: bugün paylaşılmış mı | paylaşım, reel, ek |
| `POST /{IG_ID}/media` | kaplar: resim, kaydırmalı, kapak videosu, `REELS`, `STORIES` | hepsi |
| `POST rupload.facebook.com/ig-api-upload/v26.0/{kap}` | videonun doğrudan yüklenmesi | paylaşım (kapak videosu), reel |
| `GET /{kap}?fields=status_code,status` | kap hazır mı | hepsi |
| `POST /{IG_ID}/media_publish` | paylaşım | hepsi |
| `GET /{medya}?fields=permalink,timestamp` | kayıt etiketi | paylaşım, reel, ek |

- **İzinler:** kod yalnız `instagram_content_publish`'i denetler ve izin yoksa durur. Okuma için `instagram_basic` gerekir. Başka hangi izinlerin gerektiği anahtarın türüne bağlıdır (belirsiz). Kontrol işinin günlüğündeki "izinler:" satırına bakılır.
- **Anahtar:** kısıtlama işletme portföyüne geldi. Anahtar o portföyün sistem kullanıcısına aitse geçersizleşmiş ya da izni düşmüş olabilir (belirsiz). Kontrol işi `debug_token` ile gösterir: geçersizse durur, süresine 14 günden az kaldıysa uyarır. Anahtarın yenilenmesi Meta tarafındadır ve yalnız **Rıdvan** yapar; Claude Meta sitelerinde işlem yapmaz.
- **Graph sürümü** `v26.0`'ın hâlâ geçerli olduğunu kontrol işinin ilk isteği gösterir. `YZ_ETIKETI=evet` ise `is_ai_generated` parametresi gider (belirsiz: dönüşte hâlâ destekleniyor mu).
- **GitHub tarafı:**
  - `BOT_OKUMA` ince anahtarının (yalnız `aksama-bot`, Contents: Read) süresi dolmuşsa kontrol işi 401/403 ile durur.
  - Pages kaynağı "GitHub Actions" olmalı; bunu prova gösterir.
  - İşlerin `GITHUB_TOKEN` izinleri iş dosyalarında yazılıdır: etiket için `contents: write`, Pages için `pages: write` ve `id-token: write`.
  - Google betiğinin GitHub anahtarının süresi belirsiz; yönetici bakar.

## Dönüş provası (sahte sunucu, 25 Kas)

| Soru | Kısa cevap | Sınama |
|---|---|---|
| Uzun aradan sonra yalnız o günün gönderisi mi çıkar? | Evet. Gönderi yalnız bugünün tarihiyle çıkar; eski tarih yayında reddedilir. Reel yalnız `paylasildi/<bugün>` varken ve yalnız bugünün tarihiyle çıkar: elle eski tarih (ör. 16 Kas) yayında iş kırmızı biter. Ek gönderi etiketliyse gitmez; etiketsizse yalnız `ek.json`'daki gün gider, tarihi geçmişse "süresi geçti" uyarısıyla atlanır (iş yeşil). İki açık 25 Kas'ta kapandı. | `test_donus_uzun_aradan_sonra_yalniz_bugun`, `test_donus_eski_gun_yayin_kipinde_paylasilamaz`, `DonusGerek.*`, `test_donus_eski_gun_yayin_kipinde_reel_paylasilmaz`, `test_donus_eski_gun_provada_serbest`, `test_donus_etiketsiz_eski_ek_donus_gunu_gitmez`, `test_donus_suresi_gecmis_ek_*`, `test_ertesi_gun_suresi_gecti` |
| Dönüş günü elle paylaşılmışsa çift paylaşım olur mu? | İlk satır aynı ve gönderi kaydırmalıysa olmaz (kilit 2). İlk satır farklıysa ya da tek resimse olur. Kilit 2'nin yazdığı etiket o gün reel ve ek gönderiyi başlatır. | `test_donus_gunu_elle_*`, `test_donus_aksam_gecisi_*`, `test_donus_elle_reel_*` |
| Kilitler, yedek saatler, kip ve sıra doğru mu? | Evet, iki dikkatle: tarihsiz prova ile aynı gün yayına geçilirse o gün paylaşılır; `PAYLASIM_KIPI` yanlış yazılırsa iş sessizce kontrole düşer. | `test_donus_yedek_saatler_*`, `test_donus_etiket_yazilamazsa_*`, `test_donus_kip_sirasi_*`, `test_donus_ayni_gun_prova_*`, `test_donus_paylasim_kipi_yazimi` |
| Anahtar ve izin | Yukarıdaki tablo. | `test_donus_kullanilan_uclar` (paylaşım, reel), `test_donus_anahtar_izni_ve_suresi` |
