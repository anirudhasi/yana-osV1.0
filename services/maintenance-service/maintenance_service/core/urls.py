from django.urls import path
from .views import MaintenanceLogListCreateView, MaintenanceLogDetailView, AlertListView, AlertAcknowledgeView, CostAnalyticsView

urlpatterns = [
    path("logs/",                           MaintenanceLogListCreateView.as_view(), name="log-list"),
    path("logs/<uuid:log_id>/",             MaintenanceLogDetailView.as_view(),    name="log-detail"),
    path("alerts/",                         AlertListView.as_view(),               name="alert-list"),
    path("alerts/<uuid:alert_id>/acknowledge/", AlertAcknowledgeView.as_view(),   name="alert-ack"),
    path("analytics/costs/",               CostAnalyticsView.as_view(),           name="cost-analytics"),
]
