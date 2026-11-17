# aksama-medya

Akşama Ne Var? ([@aksama.ne.var](https://www.instagram.com/aksama.ne.var/)) günlük paylaşım işi. Her sabah 09:00'da (İstanbul) günün kaydırmalı gönderisini paylaşır.

Herkese açık depodur: yalnız paylaşım kodu durur. Menüler, tarifler ve sıradaki günlerin kareleri özel depodadır; iş her sabah yalnız o günün klasörünü okur. Kareler GitHub Pages'e paylaşımdan kısa süre önce, tahmin edilemez bir adreste çıkar; ertesi gün yerini yenisine bırakır.

## Nasıl çalışır

**Kesintisiz paylaşım (13 Kas 2026):** her akşam 20:00'de yarının gönderisi Instagram'a yüklenir ama paylaşılmaz; kimliği `kap/<tarih>` etiketine yazılır. Sorun varsa akşamdan görülür. Sabah iş bu hazır gönderiyi yalnız paylaşır; içerik akşamdan sonra değiştiyse ya da hazırlık yoksa her şeyi sabah yapar. Paylaşım çıkmadıysa Google 09:10, 09:40, 11:40, 14:40 ve 17:40'ta işi yeniden başlatır; iş 23:00'e kadar paylaşır.

1. Google Apps Script "Akşama dış tetik" 08:15–08:45 arasında işi başlatır. Bu depoda GitHub saati (schedule) yoktur ve eklenmez (Rıdvan 17 Kas 09:27: "GitHub yalnız Google başlatınca paylaşır."). Reel işini de Google başlatır (09:20).
2. `hazirla`: kip ve tarih; kayıt etiketi (kilit 1); anahtar ve hesap adı kilidi (`aksama.ne.var` değilse durur); günün klasörü; denetim (onay, içerik özeti, kare biçimi, açıklama, etiket sayısı).
3. Kareler Pages'e çıkar; yayında olduğu denetlenir.
4. `yayinla`: Instagram kapları (kare başına alt metin); 09:00 beklenir; Instagram'daki bugünkü gönderilere bakılır (kilit 2); paylaşılır; `paylasildi/<tarih>` etiketi yazılır.

Bir çalıştırmada geçici hatada 290 dakikaya kadar yeniden dener; sonra Google'ın gün içi nöbetçisi devralır. Paylaşım isteği belirsiz biterse önce gidip gitmediğine bakar, aynı gün iki kez paylaşmaz. Hata olursa iş kırmızı biter (GitHub e-postası).

## Kipler

| Kip | Ne yapar |
|---|---|
| `kontrol` | Yalnız denetim. Instagram'a ve Pages'e bir şey göndermez. |
| `prova` | Paylaşım dışında her şey: kareler Pages'e çıkar, Instagram kapları hazırlanır, **paylaşılmaz** (kap 24 saatte silinir). |
| `yayin` | Gerçek paylaşım. Yalnız `PAYLASIM_KIPI=yayin` iken. |

Elle başlatırken "zaman" seçilebilir: `sabah` (paylaşım) ya da `aksam` (yarının hazırlığı, paylaşmaz). Kip seçilmezse (`otomatik`) depo değişkeni `PAYLASIM_KIPI` geçer; boşsa `kontrol`. 08:00–09:20 arasında elle kontrol ve prova yapılmaz.

## Ayarlar (Settings)

| Ad | Tür | Ne |
|---|---|---|
| `IG_TOKEN` | Secret | Meta "Aksama Ne Var" uygulamasının @aksama.ne.var anahtarı |
| `BOT_OKUMA` | Secret | İnce GitHub anahtarı: yalnız `aksama-bot`, yalnız Contents: Read-only |
| `PAYLASIM_KIPI` | Variable | `kontrol` / `prova` / `yayin` (gerçek paylaşım Rıdvan'ın onayıyla açılır) |
| `YZ_ETIKETI` | Variable | Boş ya da `hayir`: Meta "AI info" etiketi yok (Rıdvan 13 Kas 20:56); `evet`: etiket konur. YZ açıklaması her durumda açıklamanın son satırında: "Görseller temsilidir, yapay zekâ ile hazırlanmıştır." Bu satır yoksa paylaşılmaz |
| Pages | Ayar | Settings → Pages → Source: GitHub Actions |

## Deneme

`python3 paylas/test_paylas.py -v` — sahte Instagram, sahte GitHub ve sahte saatle 41 durum (akşam hazırlığı ve YZ satırı dâhil) (Pillow gerekir). Gerçek hesaba bir şey gitmez.
