# 0.13.1 — Otomatik sağmal takibi

Kaynak: lewaa131/surum-cebimde-apk, 62ee3454708eba06953751f8468073a4c3756d8a.

Doğurduğu bilinen dişi hayvan, Kuru dönemde veya Sağılmıyor değilse sağmal olarak gösterilir. Son doğum tarihi veya daha önce doğurduğuna dair kullanıcı onayı yeterlidir; bilinmeyen doğum tarihi zorunlu değildir. Yaş ve gebelik tek başına sağmal başlatmaz.

Doğdu onayı sağmalı açar; kuruya ayırma onayı kapatır. Tarih geldiğinde kendiliğinden doğdu/kuruya ayrıldı varsayılmaz. Bakım bilgileri bölümündeki Sağılmıyor seçeneği özel durumları otomatik kuralın dışında tutar. Bu seçim yeni süt girişi açmaz; önceki süt kayıtlarının düzeltilmesi mümkündür. Tekrar Sağmal seçildiğinde takip açılır.

Mevcut doğum geçmişi olan ancak Diğer durumunda kalmış kayıtlar da aynı kuralla listelenir. Hayvanlar, fotoğraflar ve süt geçmişi silinmez. Veritabanına yeni alan eklenmez.

## Yayına alma

Bu ZIP kaynak kodudur; yeni APK henüz derlenmedi ve GitHub'a gönderilmedi.
ZIP içindeki surum-cebimde klasörünün içeriğini mevcut surum-cebimde-apk deponun köküne yükle. Yeni depo açma; aynı imza Secret'ını koru.
Sürüm 0.13.1, Android sürüm kodu 100013001 olarak ayarlandı. Mevcut Actions bu kodu derleyip v0.13.1 yayınını oluşturur.
Telefonda 0.13.0 üzerinden Ayarlar → Güncellemeleri kontrol et yoluyla indir ve Android kurulumunu onayla. İlk denemeden önce uygulama dışına bir yedek kaydet.

## Kontrol

Otomatik kontroller: eski doğum kayıtlarının sağmala geçişi, tarihi bilinmeyen doğum onayı, ilk doğum öncesi gebe düve, bilinmeyen geçmiş, kuru→doğum→sağmal, buzağının sağmal olmaması ve sağılmıyor istisnası.
Yeni APK derlemesi ve gerçek telefonda 0.13.0→0.13.1 geçiş testi henüz yapılmadı.

Kaynaklar:
- https://extension.psu.edu/dairy-heifer-production
- https://extension.psu.edu/animals-and-livestock/dairy/reproduction-and-genetics
- https://extension.umn.edu/agriculture/animals-and-livestock/dairy/dairy-news/strategies-for-early-cow-dry-off
