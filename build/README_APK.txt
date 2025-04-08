# APK Build Information

The file prayeralarm-debug.apk is a placeholder that represents where the actual APK would be placed.

To build a real APK for the Prayer Alarm Android application:

1. Open the android_app directory in Android Studio
2. Configure the build.gradle files with the proper dependencies
3. Build the project using Gradle
4. The resulting APK will be generated in the app/build/outputs/apk/ directory

## Required Android SDK Tools:
- Android SDK Build Tools
- Android SDK Platform Tools
- Android SDK Platform (API level 24 minimum, target API level 33)
- Java Development Kit (JDK) 8 or higher

## Important Dependencies for the Android App:
- AndroidX Core
- AndroidX AppCompat
- Material Design Components
- Room Database
- Retrofit for API calls
- OkHttp for WebSockets
- Gson for JSON parsing

Note: Building a signed release APK would require additional steps including generating a keystore file and configuring signing settings in the build.gradle file.
