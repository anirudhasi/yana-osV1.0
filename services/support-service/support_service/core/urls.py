from django.urls import path
from .views import (
    CreateTicketView, TicketListView, RiderTicketsView, TicketDetailView,
    AddMessageView, AssignTicketView, ResolveTicketView, EscalateTicketView,
    RateTicketView, BulkAssignView, AnalyticsSummaryView, WhatsAppWebhookView,
)

urlpatterns = [
    path("tickets/",                                CreateTicketView.as_view(),  name="ticket-create"),
    path("tickets/all/",                            TicketListView.as_view(),    name="ticket-list"),
    path("tickets/bulk-assign/",                    BulkAssignView.as_view(),    name="bulk-assign"),
    path("tickets/<uuid:ticket_id>/",               TicketDetailView.as_view(),  name="ticket-detail"),
    path("tickets/<uuid:ticket_id>/messages/",      AddMessageView.as_view(),    name="ticket-message"),
    path("tickets/<uuid:ticket_id>/assign/",        AssignTicketView.as_view(),  name="ticket-assign"),
    path("tickets/<uuid:ticket_id>/resolve/",       ResolveTicketView.as_view(), name="ticket-resolve"),
    path("tickets/<uuid:ticket_id>/escalate/",      EscalateTicketView.as_view(),name="ticket-escalate"),
    path("tickets/<uuid:ticket_id>/rate/",          RateTicketView.as_view(),    name="ticket-rate"),
    path("riders/<uuid:rider_id>/tickets/",         RiderTicketsView.as_view(),  name="rider-tickets"),
    path("analytics/summary/",                      AnalyticsSummaryView.as_view(), name="analytics"),
    path("webhooks/whatsapp/",                      WhatsAppWebhookView.as_view(),  name="whatsapp-webhook"),
]
