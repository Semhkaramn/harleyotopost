# Telegram Forwarder Project

## TODO
- [ ] Web Dashboard (Next.js)
  - [ ] UI Components (Button, Card, Input, etc.)
  - [ ] Dashboard page with settings
  - [ ] API routes for bot communication
  - [ ] Statistics page
  - [ ] Post history
- [ ] Telegram Bot (Python/Telethon)
  - [ ] Main bot script
  - [ ] Message forwarding logic
  - [ ] Link extraction and cleaning
  - [ ] Daily limit system
  - [ ] Database models
- [ ] Database schema (Neon.tech PostgreSQL)
- [ ] Heroku deployment files
- [ ] Environment configuration

## Architecture
- `/src` - Next.js web dashboard (Netlify)
- `/bot` - Python Telethon bot (Heroku)
- Shared Neon.tech PostgreSQL database

Kullanıcı hem Telethon ile çalışan bir Telegram botu hem de Netlify'da ayarlar için bir web arayüzü istiyor. Tek bir GitHub repo'sunda olacak.

Yapı şöyle olacak:

Telegram Bot (Python/Telethon) - Heroku'da çalışacak
Web Dashboard (Next.js) - Netlify'da çalışacak, ayarlar için
Bunları tek bir projede birleştirmemiz gerekiyor. Web sitesi ile bot ayarlarını yönetebilecek:

Günlük post limiti
Hedef kanal
Eklenecek link
İstatistikler vs.
Veritabanı olarak Neon.tech PostgreSQL kullanılacak - her iki sistem de aynı veritabanına bağlanacak.

Bu güzel bir proje. Başlayalım.
sistem şu şekilde çalışacak hedef kanal ekleceğim normal id ile vs sonra dinleme kanalı ekleyeceğim link ile mi yoksa normal mi diye seçenek olacak link ile seçince normal telegram mesaj bağlantı linki gelince o bağlantıdaki mesjaı alıp atacak gibi normal seçince o kanala gelen direk postu atacak mesajda tetikleyici kelime veya cümle ekleceğim o varsa o postu alıp atacak sonra link ekleme yeri olacak oradan gelen postlar vs mesajın sonunda o link eklenecek ve mesajda postlarda linkler vs varsa kaldırılacak eğer link ve genel seçeneğinde linki seçersem postu hedef kanala attıktan sonra o postun mesaj bağlantısını alıp dinlenen kanala atacak dinlenen kanal eklerken post limiti de eklenecek projeme devam et oku ve eksikleri tamamla
