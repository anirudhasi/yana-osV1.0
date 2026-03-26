from django.urls import path
from .views import (
    CityListView,
    HubListCreateView, HubDetailView, HubUtilizationView,
    VehicleListCreateView, VehicleDetailView, VehicleStatusChangeView,
    VehicleGPSHistoryView, VehicleAllotmentsView,
    AllotmentListCreateView, AllotmentDetailView, AllotmentReturnView,
    AlertListView, AlertAcknowledgeView,
    FleetDashboardView,
)

urlpatterns = [
    # Cities
    path("cities/",                                        CityListView.as_view(),           name="city-list"),

    # Hubs
    path("hubs/",                                          HubListCreateView.as_view(),       name="hub-list-create"),
    path("hubs/<uuid:hub_id>/",                            HubDetailView.as_view(),           name="hub-detail"),
    path("hubs/<uuid:hub_id>/utilization/",                HubUtilizationView.as_view(),      name="hub-utilization"),

    # Vehicles
    path("vehicles/",                                      VehicleListCreateView.as_view(),   name="vehicle-list-create"),
    path("vehicles/<uuid:vehicle_id>/",                    VehicleDetailView.as_view(),       name="vehicle-detail"),
    path("vehicles/<uuid:vehicle_id>/status/",             VehicleStatusChangeView.as_view(), name="vehicle-status"),
    path("vehicles/<uuid:vehicle_id>/gps-history/",        VehicleGPSHistoryView.as_view(),   name="vehicle-gps"),
    path("vehicles/<uuid:vehicle_id>/allotments/",         VehicleAllotmentsView.as_view(),   name="vehicle-allotments"),

    # Allotments
    path("allotments/",                                    AllotmentListCreateView.as_view(), name="allotment-list-create"),
    path("allotments/<uuid:allotment_id>/",                AllotmentDetailView.as_view(),     name="allotment-detail"),
    path("allotments/<uuid:allotment_id>/return/",         AllotmentReturnView.as_view(),     name="allotment-return"),

    # Alerts
    path("alerts/",                                        AlertListView.as_view(),           name="alert-list"),
    path("alerts/<uuid:alert_id>/acknowledge/",            AlertAcknowledgeView.as_view(),    name="alert-acknowledge"),

    # Dashboard
    path("dashboard/utilization/",                         FleetDashboardView.as_view(),      name="fleet-dashboard"),
]
