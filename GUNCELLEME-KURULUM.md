# Sürüm Cebimde 0.13.0 — ilk kurulum

Bu paket gönderdiğin GITHUB-HAZIR 0.12.8 kaynakları üzerine hazırlandı. Actions önbellekleri, sabit Buildozer sürümü, açılış görseli ve mevcut kontroller korundu.

## 1. Sabit imza anahtarı — bir kez

Mevcut Actions her çalışmada geçici debug anahtarı kullanıyor. APK'nın içinden özel anahtar geri alınamaz. Eski anahtar elinde yoksa yeni sürüm eski kurulumun üzerine yüklenmeyebilir.

Windows'ta Java JDK kurulu olduğunda PowerShell ile `tools/YENI-ANAHTAR.ps1` dosyasını çalıştır. Bu işlem yeni bir anahtar oluşturur; eskisini kurtarmaz. Dosyalar Belgeler/Surum-Cebimde-Ozel-Anahtar klasörüne yazılır. Anahtar ve TXT dosyasını güvenli bir yerde ayrıca yedekle; GitHub koduna veya sohbetlere yükleme.

GitHub projesinde Settings → Secrets and variables → Actions → New repository secret:

- Name: `ANDROID_DEBUG_KEYSTORE_B64`
- Secret: oluşturulan `ANDROID_DEBUG_KEYSTORE_B64.txt` dosyasının tamamı.

İş akışı mevcut debug derleme düzenini korur; sabit `androiddebugkey` anahtarını kullanır. Secret yoksa hatalı imzayla sürüm yayımlamak yerine durur. Google Play dağıtımı bu paketin kapsamında değildir.

## 2. Kodları aynı projeye yükle

ZIP içindeki proje klasörünün içeriğini mevcut `lewaa131/surum-cebimde-apk` deposunun köküne koy. `.github/workflows/android-apk.yml` dahil olsun; fazladan bir üst klasör ekleme. Depo public olmalı; özel depodaki dosyalara erişmek için telefona GitHub parolası/token konulmaz.

`main` dalına push yapınca Actions APK'yı üretir ve `v0.13.0` Releases kaydına APK ile `update.json` dosyasını birlikte yayımlar. Henüz GitHub'a bu sohbetten push veya yayın yapılmadı.

## 3. İlk telefonu geçir

Önce mevcut uygulamada Yedekle / Geri yükle bölümünden yedeği uygulamanın dışına kaydet. Dosyanın Dosyalar/Drive üzerinden erişilebilir olduğunu doğrula. İlk 0.13.0 APK'yı Actions veya Releases üzerinden indirip kurmayı dene.

İmza uyuşmazsa kurulumu zorlamaya çalışma. Yedeğini dışarı aldığından emin olduktan sonra eski uygulamayı kaldırıp yeni uygulamayı kur ve yedeği geri yükle. Uygulamayı kaldırmak yerel kayıtları siler. İlk geçişte anahtar farkı olabilir; sonraki derlemelerde aynı Secret korunmalıdır.

## 4. Güncellemeyi dene

Önce 0.13.0 telefona kurulmalı. Daha sonra:

- `main.py`: `__version__ = "0.13.1"`
- `buildozer.spec`: `version = 0.13.1`, `android.numeric_version = 100013001`
- `RELEASE-NOTES.md`: yeni sürümün kısa açıklaması.

Push yap ve Actions'ın başarılı olmasını bekle. Telefonda Ayarlar → Güncellemeleri kontrol et → Güncelle · indir. Android gerekirse “Bu kaynaktan yüklemeye izin ver” ekranını açar. İzin verip uygulamaya dönerek Kurulumu aç'a bas; Android'in Güncelle düğmesini onayla.

Sürüm numarası her yayında artmalı. Formül: `100000000 + major*1000000 + minor*1000 + patch`. Var olan sürümün dosyaları değiştirilmez. Bir taslak yayın yarım kaldıysa Releases'teki taslağı kontrol et; eksik dosyayla yayımlama.

Uygulama açılışta arka planda kontrol eder; bağlantı yoksa çalışmaya devam eder. Açık bir formu güncelleme penceresiyle kapatmaz; Ayarlar'dan her zaman tekrar kontrol edilebilir. Kurulum sessizce yapılmaz, Android onayı gerekir. İndirme sırasında Vazgeç iptal eder.

Kontroller: internet indirmesinde dosya boyutu/SHA-256; kurulum öncesinde paket adı, artan Android sürüm kodu ve mevcut uygulamanın sertifikası. Kurulum başarısı Android'e aittir; uygulama yalnızca kurulum ekranını açtığını bildirir.
