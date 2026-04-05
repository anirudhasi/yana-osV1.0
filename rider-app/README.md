# Yana Rider App

Flutter mobile app for Yana OS riders. Covers auth (OTP), wallet, marketplace jobs, skills, and support.

## Setup

**Requirements:** Flutter 3.19+, Dart 3.3+

```bash
cd rider-app
flutter pub get
dart run build_runner build --delete-conflicting-outputs
```

## Run

```bash
# Android emulator (uses 10.0.2.2 to reach host backend)
flutter run

# Physical device — set the base URL via env or edit AppConstants.apiBaseUrl
flutter run --dart-define=API_BASE_URL=http://<your-host-ip>:8081
```

## Architecture

- **State:** Riverpod 2 with `@riverpod` code-gen annotations
- **Navigation:** GoRouter with auth redirect guard
- **HTTP:** Dio with JWT Bearer interceptor + silent token refresh
- **Storage:** flutter_secure_storage for access/refresh tokens
- **Models:** freezed + json_serializable
- **Video:** Chewie wrapping video_player, progress POSTed on completion

## Key flows

1. Launch → checks stored token → redirects to `/onboarding` if unauthenticated
2. OTP login → stores tokens → navigates to `/home`
3. Bottom nav: Wallet | Jobs | Skills | Support
4. Jobs: browse demand slots, tap to detail, apply
5. Skills: catalog list, tap to watch video, badge earned dialog on completion
6. Support: view tickets, create new ticket with category dropdown
