Pro Calculator — AdMob banner integration

Files:
- main.py: updated calculator source with Android-only KivMob banner setup.
- main.kv: reserves a strip at the bottom for the banner.

IMPORTANT Buildozer setup:
1. Add `kivmob` to the comma-separated `requirements` line in buildozer.spec
   (keep your existing requirements, e.g. python3,kivy,kivymd,kivmob).
2. Ensure the Android permissions include INTERNET and ACCESS_NETWORK_STATE.
3. Build and test using Google's test ad unit first. Do not repeatedly click your
   own live ads. Replace the banner ID with Google's official test banner ID
   while testing, then restore your real banner ID for release.
4. Confirm your AdMob app is configured and the app ID is registered in the
   Android manifest/build configuration as required by the KivMob version you use.
5. Rebuild the APK/AAB; changing Python files alone does not update an already
   installed APK.

IDs provided:
App ID: ca-app-pub-1251262394546713~8890574302
Banner ad unit: ca-app-pub-1251262394546713/1768044018

Notes:
- Ads only initialize on Android; desktop development will not show ads.
- This uses KivMob's API. Its compatibility with your current Kivy/KivyMD and
  Android Gradle setup must be confirmed by building on your existing project.
- The banner is anchored at the bottom and the KV layout reserves 56dp for it.
