"""
support_service/core/views.py

APIs:
  POST  /support/tickets/                       Create ticket (rider)
  GET   /support/tickets/                       List tickets (admin/agent)
  GET   /support/riders/{rider_id}/tickets/     Rider's own tickets
  GET   /support/tickets/{id}/                  Get ticket detail
  POST  /support/tickets/{id}/messages/         Add message (rider or agent)
  POST  /support/tickets/{id}/assign/           Assign to agent (admin)
  POST  /support/tickets/{id}/resolve/          Resolve ticket (agent)
  POST  /support/tickets/{id}/escalate/         Escalate (agent)
  POST  /support/tickets/{id}/rate/             Rate resolution (rider)
  POST  /support/tickets/bulk-assign/           Bulk assign (admin)
  GET   /support/analytics/summary/             Dashboard metrics
  POST  /support/webhooks/whatsapp/             WhatsApp webhook receiver
"""
import logging
from django.db.models import Count, Avg, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import SupportTicket, TicketMessage
from .serializers import (
    SupportTicketSerializer, CreateTicketSerializer, AddMessageSerializer,
    AssignTicketSerializer, ResolveTicketSerializer, RatingSerializer, BulkAssignSerializer,
)
from .services import create_ticket, add_message, assign_ticket, resolve_ticket, escalate_ticket, rate_ticket
from .authentication import JWTAuthentication, IsAdminUser, IsRider, IsRiderOrAdmin, IsSupportAgent, StandardPagination

logger = logging.getLogger(__name__)

def ok(data, code=200): return Response({"success": True, "data": data}, status=code)
def err(msg, code=400): return Response({"success": False, "error": {"message": msg, "code": code}}, status=code)


class CreateTicketView(APIView):
    """POST /support/tickets/ — rider creates a ticket"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request):
        s = CreateTicketSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            ticket = create_ticket(str(request.user.id), dict(s.validated_data))
            return ok(SupportTicketSerializer(ticket).data, 201)
        except Exception as e:
            logger.exception("Ticket creation failed")
            return err(str(e), 500)


class TicketListView(APIView):
    """GET /support/tickets/ — admin/agent sees all tickets"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSupportAgent]

    def get(self, request):
        qs = SupportTicket.objects.order_by("-created_at")
        for p, f in [("status","status"),("priority","priority"),("category","category"),
                     ("assigned_to_id","assigned_to_id"),("sla_breached","sla_breached")]:
            v = request.query_params.get(p)
            if v: qs = qs.filter(**{f: v == "true" if f == "sla_breached" else v})
        q = request.query_params.get("q")
        if q: qs = qs.filter(Q(ticket_number__icontains=q) | Q(subject__icontains=q))
        pager = StandardPagination()
        return pager.get_paginated_response(SupportTicketSerializer(pager.paginate_queryset(qs, request), many=True).data)


class RiderTicketsView(APIView):
    """GET /support/riders/{rider_id}/tickets/ — rider sees own tickets"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def get(self, request, rider_id):
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(rider_id):
            return err("Access denied.", 403)
        qs = SupportTicket.objects.filter(rider_id=rider_id).order_by("-created_at")
        status_f = request.query_params.get("status")
        if status_f: qs = qs.filter(status=status_f)
        pager = StandardPagination()
        return pager.get_paginated_response(SupportTicketSerializer(pager.paginate_queryset(qs, request), many=True).data)


class TicketDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def _get_ticket(self, ticket_id, request):
        try:
            t = SupportTicket.objects.get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return None
        from .authentication import AuthenticatedRider
        if isinstance(request.user, AuthenticatedRider) and str(request.user.id) != str(t.rider_id):
            return "FORBIDDEN"
        return t

    def get(self, request, ticket_id):
        t = self._get_ticket(ticket_id, request)
        if t is None: return err("Ticket not found.", 404)
        if t == "FORBIDDEN": return err("Access denied.", 403)
        return ok(SupportTicketSerializer(t).data)


class AddMessageView(APIView):
    """POST /support/tickets/{id}/messages/"""
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRiderOrAdmin]

    def post(self, request, ticket_id):
        from .authentication import AuthenticatedRider, AuthenticatedUser
        s = AddMessageSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            if isinstance(request.user, AuthenticatedRider):
                sender_type, rider_id, admin_id = "RIDER", str(request.user.id), None
                if s.validated_data["is_internal"]:
                    return err("Riders cannot add internal notes.", 403)
            else:
                sender_type, rider_id, admin_id = "AGENT", None, str(request.user.id)

            msg = add_message(
                ticket_id       = str(ticket_id),
                sender_type     = sender_type,
                message         = s.validated_data["message"],
                sender_rider_id = rider_id,
                sender_admin_id = admin_id,
                attachments     = s.validated_data.get("attachments",[]),
                is_internal     = s.validated_data["is_internal"],
            )
            from .serializers import TicketMessageSerializer
            return ok(TicketMessageSerializer(msg).data, 201)
        except ValueError as e:
            return err(str(e), 422)
        except Exception as e:
            logger.exception("Add message failed")
            return err(str(e), 500)


class AssignTicketView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSupportAgent]

    def post(self, request, ticket_id):
        s = AssignTicketSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            ticket = assign_ticket(str(ticket_id), str(s.validated_data["agent_id"]))
            return ok(SupportTicketSerializer(ticket).data)
        except ValueError as e: return err(str(e), 404)


class ResolveTicketView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSupportAgent]

    def post(self, request, ticket_id):
        s = ResolveTicketSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            ticket = resolve_ticket(str(ticket_id), str(request.user.id), s.validated_data["resolution_notes"])
            return ok(SupportTicketSerializer(ticket).data)
        except ValueError as e: return err(str(e), 422)


class EscalateTicketView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSupportAgent]

    def post(self, request, ticket_id):
        reason = request.data.get("reason","")
        try:
            ticket = escalate_ticket(str(ticket_id), str(request.user.id), reason)
            return ok(SupportTicketSerializer(ticket).data)
        except ValueError as e: return err(str(e), 404)


class RateTicketView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsRider]

    def post(self, request, ticket_id):
        s = RatingSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        try:
            ticket = rate_ticket(str(ticket_id), str(request.user.id), s.validated_data["rating"])
            return ok({"message": "Thank you for your feedback.", "rating": ticket.rider_satisfaction})
        except ValueError as e: return err(str(e), 422)


class BulkAssignView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsAdminUser]

    def post(self, request):
        s = BulkAssignSerializer(data=request.data)
        if not s.is_valid(): return Response({"success": False, "error": s.errors}, status=400)
        agent_id   = str(s.validated_data["agent_id"])
        ticket_ids = s.validated_data["ticket_ids"]
        assigned, failed = [], []
        for tid in ticket_ids:
            try:
                assign_ticket(str(tid), agent_id)
                assigned.append(str(tid))
            except Exception as e:
                failed.append({"id": str(tid), "error": str(e)})
        return ok({"assigned": len(assigned), "failed": failed})


class AnalyticsSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [IsSupportAgent]

    def get(self, request):
        from datetime import timedelta
        qs = SupportTicket.objects.all()
        today = timezone.now().date()
        week  = timezone.now() - timedelta(days=7)

        stats = qs.aggregate(
            total              = Count("id"),
            open_count         = Count("id", filter=Q(status="OPEN")),
            in_progress        = Count("id", filter=Q(status="IN_PROGRESS")),
            escalated          = Count("id", filter=Q(status="ESCALATED")),
            resolved_week      = Count("id", filter=Q(status__in=["RESOLVED","CLOSED"], resolved_at__gte=week)),
            sla_breached       = Count("id", filter=Q(sla_breached=True, status__in=["OPEN","ASSIGNED","IN_PROGRESS","ESCALATED"])),
            avg_satisfaction   = Avg("rider_satisfaction", filter=Q(rider_satisfaction__isnull=False)),
            created_today      = Count("id", filter=Q(created_at__date=today)),
        )
        by_category = list(qs.values("category").annotate(count=Count("id")).order_by("-count"))
        by_priority = list(qs.filter(status__in=["OPEN","ASSIGNED","IN_PROGRESS","ESCALATED"]).values("priority").annotate(count=Count("id")))
        return ok({"metrics": stats, "by_category": by_category, "by_priority": by_priority})


class WhatsAppWebhookView(APIView):
    """POST /support/webhooks/whatsapp/ — receive inbound WhatsApp messages."""
    permission_classes = [AllowAny]

    def get(self, request):
        # WhatsApp webhook verification
        mode      = request.query_params.get("hub.mode")
        token     = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        if mode == "subscribe" and token == "yana_whatsapp_verify":
            return Response(int(challenge), content_type="text/plain")
        return Response("Forbidden", status=403)

    def post(self, request):
        """Handle inbound WhatsApp message — create or append to ticket."""
        try:
            body = request.data
            entry = body.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            for msg_data in messages:
                phone   = msg_data.get("from","").replace("91","",1)
                text    = msg_data.get("text",{}).get("body","")
                wa_id   = msg_data.get("id","")

                if not text:
                    continue

                # Find open ticket for this rider phone
                ticket = SupportTicket.objects.filter(
                    whatsapp_thread_id=phone,
                    status__in=["OPEN","ASSIGNED","IN_PROGRESS","WAITING_RIDER"]
                ).order_by("-created_at").first()

                if ticket:
                    add_message(str(ticket.id), "RIDER", text, is_internal=False)
                    logger.info("WhatsApp reply added to ticket %s", ticket.ticket_number)
                else:
                    logger.info("No open ticket for WhatsApp %s — creating new ticket", phone)

            return ok({"received": True})
        except Exception as e:
            logger.error("WhatsApp webhook error: %s", e)
            return ok({"received": True})  # Always return 200 to WhatsApp
