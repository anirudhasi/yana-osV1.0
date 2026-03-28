from django.urls import path
from .views import (
    ClientListCreateView, ClientDetailView,
    DarkStoreListCreateView, ContractListCreateView,
    DemandSlotListCreateView, DemandSlotDetailView,
    DemandSlotPublishView, DemandSlotCancelView,
    DemandSlotApplicationsView, DemandSlotMatchesView, BulkConfirmView,
    ApplyForSlotView, WithdrawApplicationView, ApplicationDecideView,
    CheckInView, CheckOutView,
    RiderApplicationsView, SlotPayoutView,
    FillRateAnalyticsView, MarketplaceDashboardView,
)

urlpatterns = [
    # Clients & CRM
    path("clients/",                                    ClientListCreateView.as_view(),    name="client-list"),
    path("clients/<uuid:client_id>/",                   ClientDetailView.as_view(),        name="client-detail"),
    path("clients/<uuid:client_id>/dark-stores/",       DarkStoreListCreateView.as_view(), name="dark-store-list"),
    path("clients/<uuid:client_id>/contracts/",         ContractListCreateView.as_view(),  name="contract-list"),

    # Demand Slots
    path("slots/",                                      DemandSlotListCreateView.as_view(),  name="slot-list"),
    path("slots/<uuid:slot_id>/",                       DemandSlotDetailView.as_view(),      name="slot-detail"),
    path("slots/<uuid:slot_id>/publish/",               DemandSlotPublishView.as_view(),     name="slot-publish"),
    path("slots/<uuid:slot_id>/cancel/",                DemandSlotCancelView.as_view(),      name="slot-cancel"),
    path("slots/<uuid:slot_id>/applications/",          DemandSlotApplicationsView.as_view(), name="slot-apps"),
    path("slots/<uuid:slot_id>/matches/",               DemandSlotMatchesView.as_view(),     name="slot-matches"),
    path("slots/<uuid:slot_id>/bulk-confirm/",          BulkConfirmView.as_view(),           name="slot-bulk-confirm"),
    path("slots/<uuid:slot_id>/apply/",                 ApplyForSlotView.as_view(),          name="slot-apply"),
    path("slots/<uuid:slot_id>/payout/",                SlotPayoutView.as_view(),            name="slot-payout"),

    # Applications
    path("applications/<uuid:application_id>/decide/",    ApplicationDecideView.as_view(),  name="app-decide"),
    path("applications/<uuid:application_id>/withdraw/",  WithdrawApplicationView.as_view(), name="app-withdraw"),
    path("applications/<uuid:application_id>/check-in/",  CheckInView.as_view(),            name="check-in"),
    path("applications/<uuid:application_id>/check-out/", CheckOutView.as_view(),           name="check-out"),

    # Rider view
    path("riders/<uuid:rider_id>/applications/",        RiderApplicationsView.as_view(),   name="rider-apps"),

    # Analytics
    path("analytics/fill-rates/",                       FillRateAnalyticsView.as_view(),   name="fill-rates"),
    path("analytics/dashboard/",                        MarketplaceDashboardView.as_view(), name="dashboard"),
]
