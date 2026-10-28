[app]
title = InputBridge Mobile
package.name = inputbridge
package.domain = org.arvinnotdev
source.dir = .
source.include_exts = py,kv,atlas,png,jpg,ttf,json,txt
source.exclude_dirs = .git,bin,tests,ui,core,profiles,config
version = 1.0.0
requirements = python3,kivy,plyer,numpy,pyzbar
orientation = portrait
fullscreen = 0

# Keep the mobile app separate from the Windows desktop UI while sharing the
# repository's phone_client_with_auth.py implementation.
android.permissions = android.permission.INTERNET,android.permission.CAMERA
android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = False

# pyzbar is provided by this python-for-android release's recipe.
p4a.branch = v2026.05.09

[buildozer]
log_level = 2
warn_on_root = 1
