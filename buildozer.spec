[app]
title = Sürüm Cebimde
icon.filename = assets/icon.png
presplash.filename = assets/splash.png
android.presplash_color = #0C5236
package.name = surum
package.domain = org.surutakip
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json
source.exclude_dirs = tools,tests,.venv,.buildenv,__pycache__,.git,.github
version = 0.13.0
android.numeric_version = 100013000

# Python/Kivy dependencies bundled into the APK.
requirements = python3,kivy==2.3.1,pillow,certifi

# Android permissions actually used by the app.
# Gallery uses ACTION_OPEN_DOCUMENT, so storage/media permission is not needed.
android.permissions = INTERNET,CAMERA,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED,REQUEST_INSTALL_PACKAGES
android.add_src = android/src
p4a.hook = %(source.dir)s/android_hook.py
orientation = portrait
fullscreen = 0

# Current Android toolchain targets (2026).
android.api = 36
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False
android.debug_artifact = apk
android.release_artifact = aab
android.logcat_filters = *:S python:D

p4a.branch = develop
p4a.commit = fe51f56

[buildozer]
log_level = 2
warn_on_root = 1
