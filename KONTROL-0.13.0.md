# Doğrulama

- 131 Python testi geçti; sürüm karşılaştırma, yanlış paket/adres, bozuk/eksik dosya, indirme iptali ve eski dosyayı koruma dahil.
- Yeni iki Android Java sınıfı Android API jar ile derlendi.
- Masaüstünde güncelleme yok/yeni sürüm ekranları sahte sunucu cevabıyla denendi; gerçek sunucu yayını yapılmadı.
- Gönderilen kaynaklarda küpe sorgusu sonrası en üste dönme, yinelenen cevap ve çift kayıt önleme kontrol edildi.
- GitHub Actions bu ortamda çalıştırılmadı; gerçek APK derleme, kurulum izni ve yerinde güncelleme telefonda denenmeli.
- Secret veya özel anahtar bu pakete eklenmedi; bir defalık kullanıcı kurulumu gerekiyor.

Referanslar:
https://developer.android.com/studio/publish/app-signing
https://docs.github.com/en/rest/releases/releases
https://cli.github.com/manual/gh_release_create
