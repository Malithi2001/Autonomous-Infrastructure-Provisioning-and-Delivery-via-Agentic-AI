# Mobile App Guide

The mobile app uses the existing React frontend packaged with Capacitor.

```text
Android phone app -> React UI inside Capacitor -> FastAPI backend API URL
```

The FastAPI backend does not run on the phone. The phone connects to a backend running on your PC, a hosted server, or a public tunnel such as ngrok.

## 1. Run Backend For Mobile Testing

For local single-user testing without login:

```bash
cd backend
DESKTOP_MODE=true DISABLE_AUTH=true HOST=0.0.0.0 PORT=8000 ./venv/bin/python run_backend.py
```

For normal web/RBAC mode:

```bash
make backend
```

Keep the backend running while using the mobile app.

## 2. Find Your PC LAN IP

Use the LAN IP of the computer running the backend.

Windows PowerShell:

```powershell
ipconfig
```

Look for the Wi-Fi adapter IPv4 address, for example:

```text
192.168.1.10
```

macOS/Linux:

```bash
ipconfig getifaddr en0
hostname -I
```

Use this URL in the mobile app Settings page:

```text
http://192.168.1.10:8000
```

Important: `127.0.0.1` inside a phone app means the phone itself, not your PC.

## 3. Set Backend API URL In The App

Open the mobile app:

1. Go to Settings.
2. Enter the backend URL, for example `http://192.168.1.10:8000`.
3. Tap Save.
4. Tap Test Connection.

The app stores only the backend URL in localStorage. Do not store GitHub tokens in the mobile app. Configure `GITHUB_TOKEN` or GitHub App credentials in the backend `.env`.

## 4. ngrok For Mobile And Webhooks

Local GitHub webhooks require a public URL. One simple option:

```bash
ngrok http 8000
```

Use the HTTPS forwarding URL as:

```text
https://your-ngrok-url.ngrok-free.app
```

Set the GitHub webhook URL to:

```text
https://your-ngrok-url.ngrok-free.app/api/v1/webhooks/github
```

You can also enter the ngrok base URL in the mobile Settings page.

## 5. Install Mobile Dependencies

```bash
make mobile-install
```

Or directly:

```bash
cd frontend
npm install
```

## 6. Build Android App

Build and sync the React app into Android:

```bash
make mobile-sync
```

Open Android Studio:

```bash
make mobile-open-android
```

## 7. Create Debug APK

```bash
make mobile-apk-debug
```

The debug APK is generated under:

```text
frontend/android/app/build/outputs/apk/debug/
```

Install it on a phone with USB debugging:

```bash
adb install frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

You can also copy the APK to the phone and open it there.

## 8. Mobile Check

```bash
make mobile-check
```

This verifies the frontend package, Capacitor config, Android platform, env template, mobile build, and scans for obvious hardcoded secret patterns.

## 9. Limitations

- The backend must be running and reachable.
- Docker operations run on the backend machine, not on the phone.
- GitHub webhooks need a hosted backend or ngrok/public tunnel.
- GitHub tokens must be configured in the backend environment.
- Offline mode is not supported for GitHub/ML operations unless the backend is reachable.

## 10. Troubleshooting

### Android SDK Missing

Install Android Studio and the Android SDK. Open `frontend/android` in Android Studio once so it can download Gradle and SDK components.

### Backend Not Reachable

Confirm the backend is running on `0.0.0.0:8000`, not only `127.0.0.1`. Confirm the phone and PC are on the same Wi-Fi.

### CORS Problem

The backend `.env.example` includes `capacitor://localhost` and `http://localhost` in `ALLOWED_ORIGINS`. Add your hosted frontend/app origin if you deploy differently.

### Cleartext HTTP Blocked

The Android manifest enables cleartext traffic for LAN testing. Prefer HTTPS for hosted backends.

### Phone And PC Not On Same Wi-Fi

Use ngrok or host the backend publicly. A phone on mobile data cannot reach a private `192.168.x.x` PC address.
