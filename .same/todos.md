# Telegram Forwarder Project

## TODO
- [x] Web Dashboard (Next.js)
  - [x] UI Components (Button, Card, Input, etc.)
  - [x] Dashboard page with settings
  - [x] API routes for bot communication
  - [x] Statistics page
  - [x] Post history
- [x] Telegram Bot (Python/Telethon)
  - [x] Main bot script
  - [x] Message forwarding logic
  - [x] Link extraction and cleaning
  - [x] Daily limit system
  - [x] Database models
- [x] Database schema (Neon.tech PostgreSQL)
- [x] Heroku deployment files
- [x] Environment configuration

## In Progress
- [ ] Tetikleyici kelime/cümle sistemi ekleme
- [ ] Dinleme türü seçeneği (link ile / normal)
- [ ] Post sonrası link geri gönderme seçeneği
- [ ] UI'da Kanal Yönetimi sayfası
- [ ] API'lar ile gerçek veri bağlantısı

## Architecture
- `/src` - Next.js web dashboard (Netlify)
- `/bot` - Python Telethon bot (Heroku)
- Shared Neon.tech PostgreSQL database

## Sistem Özellikleri
1. Hedef kanal ekleme (normal ID ile)
2. Dinleme kanalı ekleme (link ile veya normal seçenek)
3. Tetikleyici kelime/cümle sistemi - sadece bu kelimeler içeren postlar alınacak
4. Link ekleme - postların sonuna eklenen link
5. Link temizleme - gelen postlardaki linkleri kaldır
6. Post sonrası link gönderme - hedef kanala attıktan sonra mesaj linkini dinleme kanalına gönder
7. Günlük post limiti - her dinleme kanalı için ayrı
8. İstatistikler

Kullanıcı şunları istiyor:

Shadcn bileşenlerini kendim yazmamı (CLI kullanmadan)
Günlük limit sabit 4 değil, kullanıcı kendisi seçecek
Hedef kanalları ayrı olarak ekleyecek, sonra dinleme kanalı eklerken mevcut hedef kanallar arasından seçecek
Yani iki farklı yapı olacak:

Hedef Kanallar: Sadece hedef kanal ID ve ismi
Dinleme Kanalları: Kaynak kanal + hedef kanal seçimi (dropdown) + diğer ayarlar
Önce select ve dialog bileşenlerini düzelteyim, sonra yapıyı değiştireyim.

Anlıyorum! Şimdi:

Bileşenleri kendim yazacağım
Günlük limit kullanıcının seçeceği şekilde olacak
Önce hedef kanallar eklenecek, sonra dinleme kanalı eklerken hedef kanallar listesinden seçilecek
