from django.urls import path
from .views import (
    AdminLoginView,
    RiderSendOTPView,
    RiderVerifyOTPView,
    TokenRefreshView,
    MeView,
    LogoutView,
)

urlpatterns = [
    path("admin/login",        AdminLoginView.as_view(),     name="admin-login"),
    path("rider/send-otp",     RiderSendOTPView.as_view(),   name="rider-send-otp"),
    path("rider/verify-otp",   RiderVerifyOTPView.as_view(), name="rider-verify-otp"),
    path("refresh",            TokenRefreshView.as_view(),   name="token-refresh"),
    path("me",                 MeView.as_view(),             name="auth-me"),
    path("logout",             LogoutView.as_view(),         name="logout"),
]
