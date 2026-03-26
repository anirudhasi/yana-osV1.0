"""
fleet_service/telemetry/main.py

FastAPI GPS Telemetry Sidecar
=============================
High-performance async endpoint that:
  1. Accepts GPS pings from IoT devices / mobile apps (bulk or single)
  2. Validates and buffers them in Redis
  3. Bulk-flushes to Postgres via Celery every N seconds or N records
  4. Updates vehicle live position in Postgres immediately
  5. Streams live vehicle positions via WebSocket

Runs separately from Django on port 8013.
Start: uvicorn fleet_service.telemetry.main:app --host 0.0.0.0 --port 8013
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import asyncpg
import jwt
import redis.asyncio as redis_async
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


# ─── Settings ─────────────────────────────────────────────────

class Settings(BaseSettings):
    database_url:    str = "postgres://yana_user:yana_secret@postgres:5432/yana_os"
    redis_url:       str = "redis://redis:6379/3"
    jwt_secret_key:  str = "change-me-jwt-secret-key"
    gps_batch_size:  int = 50
    gps_flush_secs:  int = 5
    celery_broker:   str = "redis://redis:6379/4"

    class Config:
        env_file = ".env"
        extra    = "ignore"

settings = Settings()


# ─── Pydantic schemas ─────────────────────────────────────────

class GPSPing(BaseModel):
    vehicle_id:  str         = Field(..., description="Vehicle UUID")
    latitude:    float       = Field(..., ge=-90,  le=90)
    longitude:   float       = Field(..., ge=-180, le=180)
    speed_kmh:   Optional[float] = Field(None, ge=0, le=250)
    battery_pct: Optional[float] = Field(None, ge=0, le=100)
    odometer_km: Optional[float] = Field(None, ge=0)
    recorded_at: Optional[datetime] = None

    @validator("vehicle_id")
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("vehicle_id must be a valid UUID")
        return v

    @validator("recorded_at", pre=True, always=True)
    def default_recorded_at(cls, v):
        return v or datetime.now(tz=timezone.utc)


class BulkGPSPing(BaseModel):
    pings: List[GPSPing] = Field(..., max_items=200)


class GPSPingResponse(BaseModel):
    accepted:    int
    buffered:    int
    vehicle_ids: List[str]


# ─── Application setup ────────────────────────────────────────

app = FastAPI(
    title="Yana OS — GPS Telemetry Sidecar",
    description="High-performance async GPS ingestion for fleet vehicles",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection pools
_redis: Optional[redis_async.Redis] = None
_pg:    Optional[asyncpg.Pool]   = None

# WebSocket connection manager
_ws_clients: dict[str, list[WebSocket]] = {}   # vehicle_id → [websockets]


# ─── Lifespan ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global _redis, _pg
    _redis = redis_async.from_url(settings.redis_url, decode_responses=True)
    _pg    = await asyncpg.create_pool(
        settings.database_url.replace("postgres://", "postgresql://"),
        min_size=2, max_size=10, command_timeout=10,
    )
    # Start background flush task
    asyncio.create_task(_gps_flush_loop())
    logger.info("Telemetry sidecar started — Redis + Postgres connected")


@app.on_event("shutdown")
async def shutdown():
    if _redis:
        await _redis.close()
    if _pg:
        await _pg.close()


# ─── Auth dependency ──────────────────────────────────────────

async def verify_token(authorization: str = Header(None)) -> dict:
    """
    Validates JWT Bearer token from auth-service.
    For IoT devices: use a special long-lived device token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ─── GPS buffer helpers ───────────────────────────────────────

BUFFER_KEY = "yana:gps:buffer"
LIVE_KEY   = "yana:gps:live:{vehicle_id}"


async def _buffer_ping(ping: GPSPing):
    """Push a GPS ping to Redis buffer list."""
    data = {
        "vehicle_id":  ping.vehicle_id,
        "latitude":    ping.latitude,
        "longitude":   ping.longitude,
        "speed_kmh":   ping.speed_kmh,
        "battery_pct": ping.battery_pct,
        "odometer_km": ping.odometer_km,
        "recorded_at": ping.recorded_at.isoformat(),
    }
    await _redis.rpush(BUFFER_KEY, json.dumps(data))

    # Update live position hash immediately
    live_key = LIVE_KEY.format(vehicle_id=ping.vehicle_id)
    await _redis.hset(live_key, mapping={
        "lat":         str(ping.latitude),
        "lng":         str(ping.longitude),
        "speed_kmh":   str(ping.speed_kmh or 0),
        "battery_pct": str(ping.battery_pct or 0),
        "odometer_km": str(ping.odometer_km or 0),
        "updated_at":  ping.recorded_at.isoformat(),
    })
    await _redis.expire(live_key, 300)    # 5 min TTL — stale if no pings


async def _flush_buffer():
    """
    Pull up to GPS_BATCH_SIZE rows from Redis buffer and bulk-insert into Postgres.
    Also updates vehicle.last_gps_lat/lng in the vehicles table.
    """
    batch_size = settings.gps_batch_size
    raw_rows   = await _redis.lrange(BUFFER_KEY, 0, batch_size - 1)
    if not raw_rows:
        return

    await _redis.ltrim(BUFFER_KEY, len(raw_rows), -1)

    rows = [json.loads(r) for r in raw_rows]

    async with _pg.acquire() as conn:
        # Bulk insert GPS history
        await conn.executemany(
            """
            INSERT INTO vehicle_gps_telemetry
                (id, vehicle_id, latitude, longitude, speed_kmh, battery_pct, odometer_km, recorded_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    str(uuid.uuid4()),
                    r["vehicle_id"],
                    r["latitude"],
                    r["longitude"],
                    r.get("speed_kmh"),
                    r.get("battery_pct"),
                    r.get("odometer_km"),
                    r["recorded_at"],
                )
                for r in rows
            ],
        )

        # Update vehicle live position (latest per vehicle)
        latest_by_vehicle: dict[str, dict] = {}
        for r in rows:
            vid = r["vehicle_id"]
            if vid not in latest_by_vehicle or r["recorded_at"] > latest_by_vehicle[vid]["recorded_at"]:
                latest_by_vehicle[vid] = r

        for vid, r in latest_by_vehicle.items():
            await conn.execute(
                """
                UPDATE vehicles
                SET last_gps_lat = $1, last_gps_lng = $2, last_gps_at = $3,
                    battery_level_pct = COALESCE($4, battery_level_pct),
                    current_odometer_km = GREATEST(current_odometer_km, COALESCE($5, 0)),
                    updated_at = NOW()
                WHERE id = $6 AND deleted_at IS NULL
                """,
                r["latitude"], r["longitude"], r["recorded_at"],
                r.get("battery_pct"), r.get("odometer_km"), vid,
            )

    # Broadcast to any subscribed WebSocket clients
    for r in rows:
        await _broadcast_to_ws(r["vehicle_id"], r)

    logger.info("Flushed %d GPS rows to Postgres", len(rows))


async def _gps_flush_loop():
    """Background coroutine: flush GPS buffer every N seconds."""
    while True:
        try:
            await _flush_buffer()
        except Exception as e:
            logger.error("GPS flush error: %s", e)
        await asyncio.sleep(settings.gps_flush_secs)


# ─── WebSocket broadcast ──────────────────────────────────────

async def _broadcast_to_ws(vehicle_id: str, data: dict):
    """Broadcast a GPS update to all subscribers watching this vehicle."""
    clients = _ws_clients.get(vehicle_id, [])
    dead    = []
    for ws in clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)


# ─── REST endpoints ───────────────────────────────────────────

@app.get("/health")
async def health():
    checks = {"service": "gps-telemetry", "status": "ok"}
    try:
        await _redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"]  = str(e)
        checks["status"] = "degraded"
    try:
        async with _pg.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = str(e)
        checks["status"]   = "degraded"
    return checks


@app.post("/telemetry/ping", response_model=GPSPingResponse)
async def ingest_single_ping(
    ping: GPSPing,
    _: dict = Depends(verify_token),
):
    """
    Ingest a single GPS ping from a vehicle IoT device or rider app.
    Buffered in Redis; flushed to Postgres in background.
    """
    await _buffer_ping(ping)
    buf_len = await _redis.llen(BUFFER_KEY)
    return GPSPingResponse(
        accepted=1,
        buffered=buf_len,
        vehicle_ids=[ping.vehicle_id],
    )


@app.post("/telemetry/ping/bulk", response_model=GPSPingResponse)
async def ingest_bulk_pings(
    payload: BulkGPSPing,
    _: dict = Depends(verify_token),
):
    """
    Bulk ingest up to 200 GPS pings (for offline batch sync).
    """
    for ping in payload.pings:
        await _buffer_ping(ping)

    buf_len = await _redis.llen(BUFFER_KEY)
    vehicle_ids = list({p.vehicle_id for p in payload.pings})

    return GPSPingResponse(
        accepted=len(payload.pings),
        buffered=buf_len,
        vehicle_ids=vehicle_ids,
    )


@app.get("/telemetry/live/{vehicle_id}")
async def get_live_position(
    vehicle_id: str,
    _: dict = Depends(verify_token),
):
    """
    Get the latest buffered GPS position for a vehicle (sub-second freshness).
    Falls back to Postgres if no Redis data.
    """
    live_key = LIVE_KEY.format(vehicle_id=vehicle_id)
    live     = await _redis.hgetall(live_key)

    if live:
        return {
            "vehicle_id":  vehicle_id,
            "source":      "redis_live",
            "latitude":    float(live.get("lat", 0)),
            "longitude":   float(live.get("lng", 0)),
            "speed_kmh":   float(live.get("speed_kmh", 0)),
            "battery_pct": float(live.get("battery_pct", 0)),
            "odometer_km": float(live.get("odometer_km", 0)),
            "updated_at":  live.get("updated_at"),
        }

    # Fall back to Postgres
    async with _pg.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT last_gps_lat, last_gps_lng, last_gps_at,
                   battery_level_pct, current_odometer_km
            FROM vehicles
            WHERE id = $1 AND deleted_at IS NULL
            """,
            vehicle_id,
        )
    if not row or not row["last_gps_lat"]:
        raise HTTPException(status_code=404, detail="No GPS data for this vehicle.")

    return {
        "vehicle_id":  vehicle_id,
        "source":      "postgres",
        "latitude":    float(row["last_gps_lat"]),
        "longitude":   float(row["last_gps_lng"]),
        "speed_kmh":   None,
        "battery_pct": float(row["battery_level_pct"] or 0),
        "odometer_km": float(row["current_odometer_km"] or 0),
        "updated_at":  row["last_gps_at"].isoformat() if row["last_gps_at"] else None,
    }


@app.get("/telemetry/fleet/live")
async def get_fleet_live_positions(
    _: dict = Depends(verify_token),
    hub_id: Optional[str] = None,
):
    """
    Get live positions of all active vehicles.
    Optionally filter by hub_id.
    """
    async with _pg.acquire() as conn:
        query = """
            SELECT v.id, v.registration_number, v.hub_id, v.status,
                   v.last_gps_lat, v.last_gps_lng, v.last_gps_at,
                   v.battery_level_pct, v.current_odometer_km
            FROM vehicles v
            WHERE v.deleted_at IS NULL
              AND v.last_gps_lat IS NOT NULL
        """
        params = []
        if hub_id:
            query += " AND v.hub_id = $1"
            params.append(hub_id)

        rows = await conn.fetch(query, *params)

    vehicles = []
    for row in rows:
        vid = str(row["id"])
        live_key = LIVE_KEY.format(vehicle_id=vid)
        live     = await _redis.hgetall(live_key)

        if live:
            lat = float(live.get("lat", row["last_gps_lat"] or 0))
            lng = float(live.get("lng", row["last_gps_lng"] or 0))
            spd = float(live.get("speed_kmh", 0))
            src = "redis_live"
        else:
            lat = float(row["last_gps_lat"] or 0)
            lng = float(row["last_gps_lng"] or 0)
            spd = 0.0
            src = "postgres"

        vehicles.append({
            "vehicle_id":           vid,
            "registration_number":  row["registration_number"],
            "hub_id":               str(row["hub_id"]),
            "status":               row["status"],
            "latitude":             lat,
            "longitude":            lng,
            "speed_kmh":            spd,
            "battery_level_pct":    float(row["battery_level_pct"] or 0),
            "current_odometer_km":  float(row["current_odometer_km"] or 0),
            "last_seen":            row["last_gps_at"].isoformat() if row["last_gps_at"] else None,
            "source":               src,
        })

    return {"count": len(vehicles), "vehicles": vehicles}


# ─── WebSocket endpoint ───────────────────────────────────────

@app.websocket("/ws/vehicle/{vehicle_id}")
async def vehicle_live_ws(websocket: WebSocket, vehicle_id: str):
    """
    WebSocket endpoint for real-time vehicle GPS tracking.
    Admin dashboard and ops apps subscribe to specific vehicle streams.

    Connect: ws://localhost:8013/ws/vehicle/{vehicle_id}
    Sends: GPS ping JSON every time a ping is received for this vehicle.
    """
    await websocket.accept()

    # Register this client
    if vehicle_id not in _ws_clients:
        _ws_clients[vehicle_id] = []
    _ws_clients[vehicle_id].append(websocket)
    logger.info("WS client connected for vehicle %s (total: %d)",
                vehicle_id, len(_ws_clients[vehicle_id]))

    # Send current position immediately on connect
    live_key = LIVE_KEY.format(vehicle_id=vehicle_id)
    live     = await _redis.hgetall(live_key)
    if live:
        await websocket.send_json({
            "vehicle_id":  vehicle_id,
            "latitude":    float(live.get("lat", 0)),
            "longitude":   float(live.get("lng", 0)),
            "speed_kmh":   float(live.get("speed_kmh", 0)),
            "battery_pct": float(live.get("battery_pct", 0)),
            "odometer_km": float(live.get("odometer_km", 0)),
            "updated_at":  live.get("updated_at"),
            "type":        "current_position",
        })

    try:
        while True:
            # Keep alive — receive pings from client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        _ws_clients[vehicle_id].remove(websocket)
        logger.info("WS client disconnected for vehicle %s", vehicle_id)


@app.websocket("/ws/fleet")
async def fleet_live_ws(websocket: WebSocket):
    """
    Fleet-wide live GPS stream for the ops dashboard map view.
    Broadcasts all vehicle positions every 5 seconds.
    """
    await websocket.accept()
    _ws_clients.setdefault("__fleet__", []).append(websocket)

    try:
        while True:
            await asyncio.sleep(5)
            async with _pg.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, registration_number, status,
                           last_gps_lat, last_gps_lng, last_gps_at
                    FROM vehicles
                    WHERE deleted_at IS NULL AND last_gps_lat IS NOT NULL
                    LIMIT 500
                    """
                )
            positions = [
                {
                    "vehicle_id":          str(r["id"]),
                    "registration_number": r["registration_number"],
                    "status":              r["status"],
                    "latitude":            float(r["last_gps_lat"]),
                    "longitude":           float(r["last_gps_lng"]),
                    "last_seen":           r["last_gps_at"].isoformat() if r["last_gps_at"] else None,
                }
                for r in rows
            ]
            await websocket.send_json({"type": "fleet_positions", "vehicles": positions})
    except WebSocketDisconnect:
        clients = _ws_clients.get("__fleet__", [])
        if websocket in clients:
            clients.remove(websocket)
