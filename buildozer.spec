[app]
# Pro Calculator Android build configuration
# Keep this file in the same folder as main.py and main.kv.

title = Pro Calculator
package.name = procalculator
package.domain = org.aryanrai

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,ttf,otf,json
source.exclude_dirs = .git,venv,.venv,bin,.buildozer,__pycache__

version = 1.0.0
orientation = portrait
fullscreen = 0

# Python/Kivy/KivyMD and AdMob bridge
requirements = python3,kivy,kivymd,android,jnius,https://github.com/MichaelStott/KivMob/archive/refs/heads/master.zip

# Android network access needed for AdMob
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Android toolchain
android.api = 36
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True
android.enable_androidx = True

# Google Mobile Ads SDK and KivMob Android bridge
android.gradle_dependencies = com.google.android.gms:play-services-ads:25.2.0,org.kivmob:kivmob-android-bridge:1.0.0
android.add_gradle_repositories = "maven { url 'https://maven.pkg.github.com/michaelstott/kivmob' }"

# AdMob App ID (production app ID)
# In main.py, use the banner ad unit ID separately.
android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-1251262394546713~8890574302

# Produce APK for debug builds and AAB for release builds
android.debug_artifact = apk
android.release_artifact = aab

# Build common Android phone architectures
android.archs = arm64-v8a, armeabi-v7a

# Helpful for reproducible automated builds
android.allow_backup = True
