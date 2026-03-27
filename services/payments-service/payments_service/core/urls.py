from django.urls import path
from .views import (
    WalletSummaryView, WalletLedgerView,
    TopUpInitiateView, TopUpConfirmView,
    AdminAdjustmentView, IncentiveCreditView,
    UPIMandateView,
    RentScheduleView, OverdueRentsView, RentScheduleCreateView,
    TransactionHistoryView,
    RazorpayWebhookView,
    AdminPaymentSummaryView,
)

urlpatterns = [
    # Wallet
    path("wallets/<uuid:rider_id>/",                     WalletSummaryView.as_view(),    name="wallet-summary"),
    path("wallets/<uuid:rider_id>/ledger/",              WalletLedgerView.as_view(),     name="wallet-ledger"),
    path("wallets/<uuid:rider_id>/topup/",               TopUpInitiateView.as_view(),    name="topup-initiate"),
    path("wallets/<uuid:rider_id>/topup/confirm/",       TopUpConfirmView.as_view(),     name="topup-confirm"),
    path("wallets/<uuid:rider_id>/adjust/",              AdminAdjustmentView.as_view(),  name="wallet-adjust"),
    path("wallets/<uuid:rider_id>/incentive/",           IncentiveCreditView.as_view(),  name="incentive-credit"),
    path("wallets/<uuid:rider_id>/upi-mandate/",         UPIMandateView.as_view(),       name="upi-mandate"),

    # Rent schedules
    path("rent/<uuid:rider_id>/schedule/",               RentScheduleView.as_view(),     name="rent-schedule"),
    path("rent/<uuid:rider_id>/overdue/",                OverdueRentsView.as_view(),     name="overdue-rents"),
    path("rent/schedule/create/",                        RentScheduleCreateView.as_view(), name="rent-schedule-create"),

    # Transactions
    path("transactions/<uuid:rider_id>/",                TransactionHistoryView.as_view(), name="transactions"),

    # Webhooks
    path("webhooks/razorpay/",                           RazorpayWebhookView.as_view(),  name="razorpay-webhook"),

    # Admin
    path("admin/summary/",                               AdminPaymentSummaryView.as_view(), name="admin-summary"),
]
