# Çalışma kuralları (aksama-medya)

Plan: claude.ai projesi "Bugün Ne Yapayım", `claude/yol-haritasi.md`. Üretim kuralları: `aksama-bot/CLAUDE.md`.

## GEÇİCİ POLİTİKA (Rıdvan 23 Kas 2026; yalnız bu proje; her şey düzelene kadar)
- Rıdvan 12:59: "yapılmayacakları önemli kararlar olarak projeye işle. ama asıl amaç ileride günlük gümüş gibi tamamaen otomatik olması. herşey düzelene kadar bu prolitika geçerli." · "çelişen kural,yazılar sistemler ne varsa geçici düzenle. dediğim gibi sonra düzelince otomatiğe alacağız."
- **Instagram'a API ile paylaşım yok.** Bu depodaki Paylaşım, Reel ve Hikâye iş akışları kapalıdır (20 Kas) ve işlerde `if: false` kilidi vardır. Rıdvan'ın açık sözü olmadan: iş akışı açılmaz, kilit kaldırılmaz, elle çalıştırılmaz, prova ya da kontrol işi başlatılmaz (onlar da Instagram'a istek atar).
- Claude tarayıcıdan Instagram ya da Meta sitelerinde işlem yapmaz. Meta tarafında anahtar, izin, uygulama değişikliği yapılmaz. Yeni sayfa ya da hesap açılmaz.
- Kod ve deneme (sahte sunucuyla) serbesttir; gerçek Instagram'a giden hiçbir şey çalıştırılmaz.
- Otomatiğe dönüş adımları ve tam metin: `claude/yol-haritasi.md` "Geçici politika". Bu bölümü yalnız Rıdvan'ın sözüyle kaldır.

## Ekip düzeni (yönetici + yazılımcılar)
- Rıdvan 23 Kasım 2026 13:40: "günlük gümüş dışında hepsinde başla." · 13:47: "bütün yeni projeler ekip ile başlamalı. benim muhattabım . yönetici olmalı. benim seçimime gerek yok yönetici aşırı risk içermeyen gerekli kararları alır rapor verir." Ajanlar `.claude/agents/`, varsayılan ajan modeli `.claude/settings.json` (opus). Ortak kural: proje-calisma-duzeni becerisi, bölüm 13.
- Ana sohbet her zaman yöneticidir ve Rıdvan'ın muhatabıdır. Rıdvan'dan model seçimi beklenmez: yönetici sohbetin modeliyle çalışır, ajanların modelini kendisi seçer.
- Yönetici işi böler, ajanlara verir, denetler, yol haritasını günceller ve rapor verir. Kodu kendisi yazmaz (birkaç satırlık düzeltme hariç).
- Görevler `yazilimci` (Opus) ajanına verilir; bağımsız görevler aynı anda verilebilir. Her teslim `testci` (Opus) ile denenir; denenmeden "bitti" denmez.
- `kidemli-yazilimci` (Fable): büyük işin planı ve mimarisi, güvenlik, yeni algoritma, zor hata, Opus'un iki denemede çözemediği iş. Çağırmadan önce gerekçe tek satırla yazılır.
- Yönetici olağan kararları (iş bölümü, teknik yol, sıra, ajan ve model seçimi) kendisi alır, raporda bildirir ve yol haritasına "Yönetici kararı" diye yazar. Rıdvan'da kalanlar: bu dosyada Rıdvan'ın kararı ya da onayı denen konular, geçici politikalar, onaylı metinler, alarm/karar kuralı değişikliği, geri alınamaz işlemler (silme, yayına alma, para, gönderme).
