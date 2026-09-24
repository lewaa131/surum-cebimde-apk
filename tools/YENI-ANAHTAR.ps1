# Run once. Keep this private folder outside the GitHub project.
$ErrorActionPreference = 'Stop'
$keyToolCommand = Get-Command keytool -ErrorAction SilentlyContinue
if (!$keyToolCommand) { throw 'Java JDK kur ve bu dosyayi tekrar calistir: keytool bulunamadi.' }
$keyFolder = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Surum-Cebimde-Ozel-Anahtar'
New-Item -ItemType Directory -Path $keyFolder -Force | Out-Null
$keyFile = Join-Path $keyFolder 'debug.keystore'
if (Test-Path -LiteralPath $keyFile) { throw 'Anahtar zaten var. Uzerine yazilmadi; mevcut anahtari kullan.' }
& $keyToolCommand.Source -genkeypair -keystore $keyFile -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=Surum Cebimde, O=Surum Cebimde, C=TR'
if ($LASTEXITCODE -ne 0) { throw 'Anahtar olusturulamadi.' }
$secretFile = Join-Path $keyFolder 'ANDROID_DEBUG_KEYSTORE_B64.txt'
[IO.File]::WriteAllText($secretFile,[Convert]::ToBase64String([IO.File]::ReadAllBytes($keyFile)))
Write-Host "Olusturuldu: $keyFolder"
Write-Host 'TXT icerigini GitHub Actions secret ANDROID_DEBUG_KEYSTORE_B64 olarak kaydet.'
Write-Host 'Bu iki dosyayi GitHub koduna yukleme. Guvenli bir yerde yedekle.'
