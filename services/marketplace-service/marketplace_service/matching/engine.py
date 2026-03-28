"""
marketplace_service/matching/engine.py

Rider–Demand Matching Engine
=============================
Scores and ranks eligible riders for a given demand slot using
a multi-factor algorithm. Designed to be extended with ML scores
in Phase 3 (AI layer).

Scoring factors:
  1. Distance from rider's hub to dark store     (40% weight)
  2. Rider reliability score                     (30% weight)
  3. Shift experience (past completions)         (20% weight)
  4. Response speed (how quickly they apply)     (10% weight)

Returns an ordered list of RiderMatch objects with a composite score.
"""
import logging
import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from django.db.models import Count, Q

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────

@dataclass
class RiderProfile:
    rider_id:          str
    full_name:         str
    phone:             str
    hub_id:            Optional[str]
    city_id:           Optional[str]
    hub_lat:           Optional[float]
    hub_lng:           Optional[float]
    reliability_score: float = 0.0
    total_completions: int   = 0
    recent_no_shows:   int   = 0
    has_vehicle:       bool  = True


@dataclass
class DemandSlotSpec:
    slot_id:              str
    city_id:              str
    dark_store_lat:       Optional[float]
    dark_store_lng:       Optional[float]
    min_reliability:      float
    required_hub_ids:     List[str]
    badge_required:       Optional[str]
    riders_required:      int
    riders_confirmed:     int
    vehicle_required:     bool


@dataclass(order=True)
class RiderMatch:
    score:             float
    rider_id:          str      = field(compare=False)
    full_name:         str      = field(compare=False)
    distance_km:       float    = field(compare=False)
    reliability_score: float    = field(compare=False)
    total_completions: int      = field(compare=False)
    score_breakdown:   dict     = field(compare=False, default_factory=dict)


# ── Geo utilities ─────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine great-circle distance in km."""
    R  = 6371.0
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a  = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Scoring functions ─────────────────────────────────────────

def _distance_score(distance_km: float, max_radius_km: float = 10.0) -> float:
    """
    Score 1.0 for zero distance, 0.0 for distance >= max_radius_km.
    Linear decay within radius.
    """
    if distance_km >= max_radius_km:
        return 0.0
    return 1.0 - (distance_km / max_radius_km)


def _reliability_score_normalised(score: float) -> float:
    """Normalise 0–10 reliability score to 0–1."""
    return min(max(score, 0.0), 10.0) / 10.0


def _experience_score(completions: int, no_shows: int) -> float:
    """
    Sigmoid-like experience score. Tops out at ~50 completions.
    Penalises no-shows heavily.
    """
    base    = min(completions, 50) / 50.0
    penalty = min(no_shows * 0.15, 0.5)
    return max(0.0, base - penalty)


def _compute_composite_score(
    distance_km: float,
    reliability: float,
    completions: int,
    no_shows:    int,
    weights:     dict = None,
) -> tuple[float, dict]:
    """
    Weighted composite score in [0, 1].
    Returns (score, breakdown_dict).
    """
    w = weights or {
        "distance":    0.40,
        "reliability": 0.30,
        "experience":  0.20,
        "response":    0.10,   # applied early → bonus (handled outside)
    }

    d_score  = _distance_score(distance_km)
    r_score  = _reliability_score_normalised(reliability)
    e_score  = _experience_score(completions, no_shows)

    composite = (
        w["distance"]    * d_score  +
        w["reliability"] * r_score  +
        w["experience"]  * e_score
    )

    breakdown = {
        "distance_score":    round(d_score,   3),
        "reliability_score": round(r_score,   3),
        "experience_score":  round(e_score,   3),
        "composite":         round(composite, 3),
        "distance_km":       round(distance_km, 2),
        "weights":           w,
    }
    return round(composite, 4), breakdown


# ── Eligibility checks ────────────────────────────────────────

def _is_eligible(rider: RiderProfile, slot: DemandSlotSpec,
                 max_radius_km: float) -> tuple[bool, str]:
    """
    Hard eligibility gates before scoring.
    Returns (eligible, reason_if_not).
    """
    # City restriction
    if slot.city_id and rider.city_id and str(rider.city_id) != str(slot.city_id):
        return False, "city_mismatch"

    # Hub restriction
    if slot.required_hub_ids and str(rider.hub_id) not in slot.required_hub_ids:
        return False, "hub_not_in_required"

    # Reliability minimum
    if rider.reliability_score < slot.min_reliability:
        return False, f"reliability_too_low ({rider.reliability_score} < {slot.min_reliability})"

    # Vehicle check
    if slot.vehicle_required and not rider.has_vehicle:
        return False, "no_vehicle"

    # Distance check (only if geo data available)
    if (slot.dark_store_lat and slot.dark_store_lng
            and rider.hub_lat and rider.hub_lng):
        dist = _haversine_km(
            rider.hub_lat, rider.hub_lng,
            slot.dark_store_lat, slot.dark_store_lng,
        )
        if dist > max_radius_km:
            return False, f"too_far ({dist:.1f} km > {max_radius_km} km)"

    return True, ""


# ── Main engine ───────────────────────────────────────────────

def find_matching_riders(
    slot:             DemandSlotSpec,
    rider_profiles:   List[RiderProfile],
    max_radius_km:    float = 10.0,
    top_n:            int   = 50,
) -> List[RiderMatch]:
    """
    Score and rank riders for a demand slot.

    Args:
        slot:           Demand slot specification
        rider_profiles: All candidate riders to consider
        max_radius_km:  Maximum distance from hub to dark store
        top_n:          Return only top N matches

    Returns:
        Sorted list of RiderMatch (highest score first)
    """
    matches  = []
    rejected = {"city_mismatch": 0, "hub_not_in_required": 0,
                "reliability_too_low": 0, "no_vehicle": 0,
                "too_far": 0, "other": 0}

    for rider in rider_profiles:
        eligible, reason = _is_eligible(rider, slot, max_radius_km)
        if not eligible:
            key = reason.split(" ")[0]
            rejected[key if key in rejected else "other"] = rejected.get(key, 0) + 1
            continue

        # Compute distance
        if (slot.dark_store_lat and slot.dark_store_lng
                and rider.hub_lat and rider.hub_lng):
            dist = _haversine_km(
                rider.hub_lat, rider.hub_lng,
                slot.dark_store_lat, slot.dark_store_lng,
            )
        else:
            dist = 0.0  # No geo data — treat as co-located

        score, breakdown = _compute_composite_score(
            distance_km  = dist,
            reliability  = rider.reliability_score,
            completions  = rider.total_completions,
            no_shows     = rider.recent_no_shows,
        )

        matches.append(RiderMatch(
            score             = score,
            rider_id          = rider.rider_id,
            full_name         = rider.full_name,
            distance_km       = dist,
            reliability_score = rider.reliability_score,
            total_completions = rider.total_completions,
            score_breakdown   = breakdown,
        ))

    # Sort descending by score
    matches.sort(reverse=True)

    logger.info(
        "Matching for slot %s: %d candidates, %d eligible, %d in top-%d | rejected: %s",
        slot.slot_id, len(rider_profiles), len(matches),
        min(len(matches), top_n), top_n, rejected,
    )
    return matches[:top_n]


def load_rider_profiles_for_slot(slot) -> List[RiderProfile]:
    """
    Load RiderProfile objects for all ACTIVE riders who haven't already
    applied or been confirmed for this slot.
    """
    from marketplace_service.core.models import DemandApplication, Rider

    # Riders already engaged with this slot
    applied_ids = set(
        DemandApplication.objects.filter(
            demand_slot=slot,
            status__in=["APPLIED", "SHORTLISTED", "CONFIRMED"],
        ).values_list("rider_id", flat=True)
    )

    # Get all active riders
    riders = Rider.objects.filter(status="ACTIVE").exclude(id__in=applied_ids)

    # Get completion counts
    completions = dict(
        DemandApplication.objects.filter(
            rider_id__in=riders.values_list("id", flat=True),
            status="COMPLETED",
        ).values("rider_id").annotate(c=Count("id")).values_list("rider_id", "c")
    )

    no_shows = dict(
        DemandApplication.objects.filter(
            rider_id__in=riders.values_list("id", flat=True),
            status="NO_SHOW",
        ).values("rider_id").annotate(c=Count("id")).values_list("rider_id", "c")
    )

    profiles = []
    for r in riders:
        profiles.append(RiderProfile(
            rider_id          = str(r.id),
            full_name         = r.full_name,
            phone             = r.phone,
            hub_id            = str(r.hub_id) if r.hub_id else None,
            city_id           = str(r.city_id) if r.city_id else None,
            hub_lat           = float(r.latitude)  if r.latitude  else None,
            hub_lng           = float(r.longitude) if r.longitude else None,
            reliability_score = float(r.reliability_score or 0),
            total_completions = completions.get(r.id, 0),
            recent_no_shows   = no_shows.get(r.id, 0),
            has_vehicle       = True,  # fleet-service owns this; assume True for now
        ))

    return profiles
