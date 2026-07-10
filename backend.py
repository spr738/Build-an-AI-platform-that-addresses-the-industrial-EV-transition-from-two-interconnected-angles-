Now let me create all the backend and frontend files in parallel.
Action: file_editor create /app/backend/server.py --file-text "from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os, logging, uuid, random, hashlib, hmac, base64, json
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt as pyjwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
JWT_ALGO = \"HS256\"
JWT_EXP_HOURS = 24 * 7

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title=\"Voltcore — Industrial EV Ops Platform\")
api = APIRouter(prefix=\"/api\")
security = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(\"voltcore\")


# ============ MODELS ============
class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class ChatInput(BaseModel):
    message: str
    context: Optional[str] = None  # \"fleet\" | \"manufacturer\"
    session_id: Optional[str] = None

class WorkOrderPatch(BaseModel):
    status: Literal[\"backlog\", \"diagnosing\", \"in_progress\", \"completed\"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def make_token(user_id: str, email: str) -> str:
    payload = {
        \"sub\": user_id,
        \"email\": email,
        \"exp\": datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HOURS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    if not cred:
        raise HTTPException(status_code=401, detail=\"Missing bearer token\")
    try:
        payload = pyjwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except pyjwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f\"Invalid token: {e}\")
    return payload


# ============ AUTH ============
@api.post(\"/auth/register\")
async def register(inp: RegisterInput):
    existing = await db.users.find_one({\"email\": inp.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail=\"Email already registered\")
    uid = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(inp.password.encode(), bcrypt.gensalt()).decode()
    doc = {
        \"id\": uid,
        \"email\": inp.email.lower(),
        \"name\": inp.name,
        \"pw_hash\": pw_hash,
        \"created_at\": now_iso(),
    }
    await db.users.insert_one(doc)
    return {\"token\": make_token(uid, inp.email.lower()), \"user\": {\"id\": uid, \"email\": inp.email.lower(), \"name\": inp.name}}


@api.post(\"/auth/login\")
async def login(inp: LoginInput):
    doc = await db.users.find_one({\"email\": inp.email.lower()})
    if not doc or not bcrypt.checkpw(inp.password.encode(), doc[\"pw_hash\"].encode()):
        raise HTTPException(status_code=401, detail=\"Invalid credentials\")
    return {\"token\": make_token(doc[\"id\"], doc[\"email\"]), \"user\": {\"id\": doc[\"id\"], \"email\": doc[\"email\"], \"name\": doc[\"name\"]}}


@api.get(\"/auth/me\")
async def me(user=Depends(current_user)):
    doc = await db.users.find_one({\"id\": user[\"sub\"]}, {\"_id\": 0, \"pw_hash\": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=\"User not found\")
    return doc


# ============ FLEET ENDPOINTS ============
@api.get(\"/fleet/overview\")
async def fleet_overview(user=Depends(current_user)):
    vehicles = await db.vehicles.find({}, {\"_id\": 0}).to_list(500)
    alerts = await db.alerts.find({}, {\"_id\": 0}).to_list(500)
    work_orders = await db.work_orders.find({}, {\"_id\": 0}).to_list(500)
    total = len(vehicles)
    active = sum(1 for v in vehicles if v[\"status\"] == \"active\")
    charging = sum(1 for v in vehicles if v[\"status\"] == \"charging\")
    down = sum(1 for v in vehicles if v[\"status\"] == \"down\")
    avg_soh = round(sum(v[\"battery_soh\"] for v in vehicles) / max(total, 1), 1)
    energy_kwh = sum(v[\"energy_today_kwh\"] for v in vehicles)
    utilization = round(sum(v[\"utilization\"] for v in vehicles) / max(total, 1), 1)
    critical_alerts = sum(1 for a in alerts if a[\"severity\"] == \"critical\")
    open_wo = sum(1 for w in work_orders if w[\"status\"] != \"completed\")
    # trend data
    trend = [
        {\"t\": (datetime.now(timezone.utc) - timedelta(hours=23 - i)).strftime(\"%H:00\"),
         \"kwh\": round(random.uniform(220, 480), 1),
         \"utilization\": round(random.uniform(58, 92), 1)}
        for i in range(24)
    ]
    return {
        \"kpis\": {
            \"total_vehicles\": total,
            \"active\": active,
            \"charging\": charging,
            \"down\": down,
            \"avg_battery_soh\": avg_soh,
            \"energy_today_kwh\": round(energy_kwh, 1),
            \"utilization_pct\": utilization,
            \"critical_alerts\": critical_alerts,
            \"open_work_orders\": open_wo,
        },
        \"trend\": trend,
    }


@api.get(\"/fleet/vehicles\")
async def list_vehicles(user=Depends(current_user)):
    vehicles = await db.vehicles.find({}, {\"_id\": 0}).to_list(500)
    return vehicles


@api.get(\"/fleet/vehicles/{vid}\")
async def vehicle_detail(vid: str, user=Depends(current_user)):
    v = await db.vehicles.find_one({\"id\": vid}, {\"_id\": 0})
    if not v:
        raise HTTPException(status_code=404, detail=\"Vehicle not found\")
    # telemetry (30 mins samples)
    v[\"telemetry\"] = [
        {\"t\": (datetime.now(timezone.utc) - timedelta(minutes=(29 - i) * 2)).strftime(\"%H:%M\"),
         \"pack_temp\": round(28 + random.uniform(-2, 6), 1),
         \"voltage\": round(v[\"voltage_v\"] + random.uniform(-4, 4), 1),
         \"current\": round(random.uniform(-160, 220), 1)}
        for i in range(30)
    ]
    return v


@api.get(\"/fleet/alerts\")
async def list_alerts(user=Depends(current_user)):
    alerts = await db.alerts.find({}, {\"_id\": 0}).sort(\"created_at\", -1).to_list(200)
    return alerts


@api.get(\"/fleet/work-orders\")
async def list_work_orders(user=Depends(current_user)):
    wos = await db.work_orders.find({}, {\"_id\": 0}).to_list(500)
    return wos


@api.patch(\"/fleet/work-orders/{wid}\")
async def patch_wo(wid: str, patch: WorkOrderPatch, user=Depends(current_user)):
    res = await db.work_orders.update_one({\"id\": wid}, {\"$set\": {\"status\": patch.status, \"updated_at\": now_iso()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail=\"Work order not found\")
    return {\"ok\": True}


@api.get(\"/fleet/procurement\")
async def procurement(user=Depends(current_user)):
    recs = await db.procurement.find({}, {\"_id\": 0}).to_list(200)
    return recs


# ============ MANUFACTURER ENDPOINTS ============
@api.get(\"/manufacturer/overview\")
async def mfg_overview(user=Depends(current_user)):
    sup = await db.suppliers.find({}, {\"_id\": 0}).to_list(500)
    inc = await db.quality_incidents.find({}, {\"_id\": 0}).to_list(500)
    bom = await db.bom.find({}, {\"_id\": 0}).to_list(500)
    return {
        \"kpis\": {
            \"total_suppliers\": len(sup),
            \"high_risk_suppliers\": sum(1 for s in sup if s[\"risk_score\"] >= 70),
            \"avg_ppm\": round(sum(s[\"ppm\"] for s in sup) / max(len(sup), 1), 1),
            \"avg_otd\": round(sum(s[\"otd_pct\"] for s in sup) / max(len(sup), 1), 1),
            \"open_incidents\": sum(1 for i in inc if i[\"status\"] != \"closed\"),
            \"critical_bom_parts\": sum(1 for b in bom if b[\"criticality\"] == \"A\"),
        }
    }


@api.get(\"/manufacturer/suppliers\")
async def list_suppliers(user=Depends(current_user)):
    return await db.suppliers.find({}, {\"_id\": 0}).to_list(500)


@api.get(\"/manufacturer/quality\")
async def quality(user=Depends(current_user)):
    return await db.quality_incidents.find({}, {\"_id\": 0}).sort(\"opened_at\", -1).to_list(500)


@api.get(\"/manufacturer/risk\")
async def risk_heatmap(user=Depends(current_user)):
    categories = [\"Cells\", \"Power Electronics\", \"E-Motors\", \"Rare Earths\", \"Semiconductors\", \"Wiring Harness\"]
    regions = [\"China\", \"SE Asia\", \"Europe\", \"North America\", \"India\"]
    # deterministic-ish random using seeded values stored
    cache = await db.risk_matrix.find_one({\"id\": \"matrix-v1\"}, {\"_id\": 0})
    if cache:
        return cache
    cells = []
    for c in categories:
        for r in regions:
            cells.append({
                \"category\": c, \"region\": r,
                \"score\": random.randint(15, 95),
                \"notes\": random.choice([
                    \"Geopolitical exposure elevated\",
                    \"Single-source dependency\",
                    \"Lead-time variance rising\",
                    \"Compliance stable\",
                    \"Tariff risk under monitoring\",
                ])
            })
    matrix = {\"id\": \"matrix-v1\", \"categories\": categories, \"regions\": regions, \"cells\": cells}
    await db.risk_matrix.insert_one(matrix.copy())
    return matrix


@api.get(\"/manufacturer/bom\")
async def bom(user=Depends(current_user)):
    return await db.bom.find({}, {\"_id\": 0}).to_list(500)


# ============ AI COPILOT (streaming SSE) ============
@api.post(\"/copilot/chat\")
async def copilot(inp: ChatInput, user=Depends(current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

    sess = inp.session_id or f\"{user['sub']}-{uuid.uuid4()}\"
    ctx = \"fleet operations (predictive maintenance, telemetry, work orders, procurement)\" if inp.context == \"fleet\" \
        else \"EV manufacturing (supplier quality, supply-chain risk, BOM criticality)\"
    system_message = (
        \"You are Voltcore Copilot, an analytical AI for industrial EV operations. \"
        f\"The user is currently working in the {ctx} context. \"
        \"Respond concisely with structured, actionable insights. \"
        \"Use short paragraphs and bullet points. Reference metrics numerically when useful. \"
        \"Never fabricate specific numbers you don't have — reason at a strategic level.\"
    )

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=sess, system_message=system_message).with_model(\"anthropic\", \"claude-sonnet-4-6\")

    async def event_generator():
        try:
            async for ev in chat.stream_message(UserMessage(text=inp.message)):
                if isinstance(ev, TextDelta):
                    yield f\"data: {json.dumps({'delta': ev.content})}\n\n\"
                elif isinstance(ev, StreamDone):
                    yield f\"data: {json.dumps({'done': True, 'session_id': sess})}\n\n\"
                    break
        except Exception as e:
            yield f\"data: {json.dumps({'error': str(e)})}\n\n\"

    return StreamingResponse(event_generator(), media_type=\"text/event-stream\",
                             headers={\"Cache-Control\": \"no-cache\", \"X-Accel-Buffering\": \"no\", \"Connection\": \"keep-alive\"})


# ============ SEED ============
async def seed_db():
    # skip if already seeded
    if await db.vehicles.count_documents({}) > 0:
        return
    logger.info(\"Seeding demo data…\")

    # demo user
    if not await db.users.find_one({\"email\": \"demo@voltcore.io\"}):
        uid = str(uuid.uuid4())
        pw = bcrypt.hashpw(b\"demo1234\", bcrypt.gensalt()).decode()
        await db.users.insert_one({\"id\": uid, \"email\": \"demo@voltcore.io\", \"name\": \"Demo Operator\", \"pw_hash\": pw, \"created_at\": now_iso()})

    models = [\"Volvo FH Electric\", \"Tesla Semi\", \"Freightliner eCascadia\", \"MAN eTGX\", \"BYD 8TT\"]
    depots = [\"Rotterdam-01\", \"Hamburg-02\", \"Antwerp-03\", \"Duisburg-04\"]
    statuses = [\"active\", \"active\", \"active\", \"charging\", \"down\"]
    vehicles = []
    for i in range(14):
        soh = round(random.uniform(72, 99), 1)
        status = random.choice(statuses)
        vehicles.append({
            \"id\": f\"VC-{1001+i}\",
            \"vin\": f\"1EVX{random.randint(10000000, 99999999)}\",
            \"model\": random.choice(models),
            \"depot\": random.choice(depots),
            \"status\": status,
            \"battery_soh\": soh,
            \"state_of_charge\": round(random.uniform(18, 96), 1),
            \"range_km\": round(random.uniform(120, 480), 0),
            \"odometer_km\": random.randint(48000, 320000),
            \"voltage_v\": round(random.uniform(700, 800), 1),
            \"motor_temp_c\": round(random.uniform(38, 78), 1),
            \"brake_wear_pct\": round(random.uniform(5, 82), 1),
            \"energy_today_kwh\": round(random.uniform(80, 640), 1),
            \"utilization\": round(random.uniform(45, 96), 1),
            \"next_service_km\": random.randint(500, 12000),
            \"created_at\": now_iso(),
        })
    await db.vehicles.insert_many(vehicles)

    alert_types = [
        (\"battery_degradation\", \"Battery SoH decline exceeds forecast\"),
        (\"motor_overtemp\", \"Motor bearing temperature anomaly detected\"),
        (\"brake_wear\", \"Brake pad wear approaching threshold\"),
        (\"charging_inefficiency\", \"DC fast charge efficiency drop 6.2%\"),
        (\"thermal_runaway_risk\", \"Cell voltage divergence in pack module 3\"),
    ]
    alerts = []
    for i in range(11):
        v = random.choice(vehicles)
        code, msg = random.choice(alert_types)
        severity = random.choice([\"critical\", \"warning\", \"warning\", \"info\"])
        alerts.append({
            \"id\": str(uuid.uuid4()),
            \"vehicle_id\": v[\"id\"],
            \"code\": code,
            \"message\": msg,
            \"severity\": severity,
            \"predicted_failure_days\": random.randint(3, 42),
            \"created_at\": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 96))).isoformat(),
        })
    await db.alerts.insert_many(alerts)

    wo_status = [\"backlog\", \"diagnosing\", \"in_progress\", \"completed\"]
    techs = [\"A. Kruger\", \"M. Chen\", \"S. Petrov\", \"L. Okafor\", \"R. Sato\"]
    priority = [\"P1\", \"P2\", \"P3\"]
    tasks_pool = [
        \"Replace HV coolant pump\",
        \"Recalibrate regen braking module\",
        \"Inspect battery module M3\",
        \"Firmware update: BMS 4.2.1\",
        \"Motor stator resistance test\",
        \"DC fast-charge inlet inspection\",
        \"Torque check drive-shaft\",
        \"Cell balancing procedure\",
        \"Thermal paste re-application\",
        \"Onboard charger diagnostic\",
    ]
    wos = []
    for t in tasks_pool:
        v = random.choice(vehicles)
        wos.append({
            \"id\": str(uuid.uuid4()),
            \"title\": t,
            \"vehicle_id\": v[\"id\"],
            \"assignee\": random.choice(techs),
            \"priority\": random.choice(priority),
            \"status\": random.choice(wo_status),
            \"eta_hours\": random.randint(1, 12),
            \"created_at\": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 14))).isoformat(),
            \"updated_at\": now_iso(),
        })
    await db.work_orders.insert_many(wos)

    proc = [
        {\"id\": str(uuid.uuid4()), \"vehicle\": \"Volvo FH Electric 6x2\", \"tco_5yr_usd\": 428000, \"range_km\": 380, \"payload_t\": 22, \"score\": 88, \"note\": \"Best-in-class TCO for long-haul depots\"},
        {\"id\": str(uuid.uuid4()), \"vehicle\": \"Tesla Semi\", \"tco_5yr_usd\": 462000, \"range_km\": 500, \"payload_t\": 20, \"score\": 84, \"note\": \"Highest range; supercharger dependency\"},
        {\"id\": str(uuid.uuid4()), \"vehicle\": \"Freightliner eCascadia\", \"tco_5yr_usd\": 445000, \"range_km\": 370, \"payload_t\": 21, \"score\": 82, \"note\": \"Strong service network in NA\"},
        {\"id\": str(uuid.uuid4()), \"vehicle\": \"MAN eTGX\", \"tco_5yr_usd\": 438000, \"range_km\": 350, \"payload_t\": 22, \"score\": 80, \"note\": \"Modular battery, EU-optimized\"},
        {\"id\": str(uuid.uuid4()), \"vehicle\": \"BYD 8TT\", \"tco_5yr_usd\": 395000, \"range_km\": 320, \"payload_t\": 22, \"score\": 78, \"note\": \"Lower CAPEX; LFP chemistry\"},
    ]
    await db.procurement.insert_many(proc)

    supplier_pool = [
        (\"CATL\", \"China\", \"cells\"),
        (\"LG Energy Solution\", \"SE Asia\", \"cells\"),
        (\"Samsung SDI\", \"SE Asia\", \"cells\"),
        (\"Bosch Power\", \"Europe\", \"power_electronics\"),
        (\"Infineon\", \"Europe\", \"semiconductors\"),
        (\"Nidec\", \"SE Asia\", \"e-motors\"),
        (\"ZF Friedrichshafen\", \"Europe\", \"e-motors\"),
        (\"Sumitomo\", \"SE Asia\", \"wiring_harness\"),
        (\"Aptiv\", \"North America\", \"wiring_harness\"),
        (\"MP Materials\", \"North America\", \"rare_earths\"),
    ]
    suppliers = []
    for n, region, cat in supplier_pool:
        risk = random.randint(20, 90)
        suppliers.append({
            \"id\": str(uuid.uuid4()),
            \"name\": n,
            \"region\": region,
            \"category\": cat,
            \"quality_grade\": random.choice([\"A\", \"A\", \"B\", \"B\", \"C\"]),
            \"ppm\": random.randint(35, 820),
            \"otd_pct\": round(random.uniform(84, 99.5), 1),
            \"lead_time_days\": random.randint(14, 120),
            \"risk_score\": risk,
            \"single_source\": random.random() < 0.35,
            \"spend_musd\": round(random.uniform(4, 240), 1),
            \"last_audit\": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 400))).strftime(\"%Y-%m-%d\"),
        })
    await db.suppliers.insert_many(suppliers)

    incidents = []
    inc_titles = [
        \"Weld porosity — busbar\",
        \"Coolant hose micro-leak\",
        \"BMS firmware anomaly\",
        \"Cell voltage drift > 40mV\",
        \"Motor bearing tolerance out-of-spec\",
        \"Wiring harness abrasion at loom bend\",
        \"Torque spec deviation — drive unit\",
    ]
    for t in inc_titles:
        s = random.choice(suppliers)
        incidents.append({
            \"id\": str(uuid.uuid4()),
            \"title\": t,
            \"supplier_id\": s[\"id\"],
            \"supplier_name\": s[\"name\"],
            \"severity\": random.choice([\"low\", \"medium\", \"high\", \"critical\"]),
            \"status\": random.choice([\"open\", \"in_review\", \"contained\", \"closed\"]),
            \"opened_at\": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))).isoformat(),
            \"affected_units\": random.randint(1, 1200),
            \"root_cause\": random.choice([\"process variation\", \"raw material lot\", \"operator error\", \"tooling wear\", \"design tolerance\"]),
        })
    await db.quality_incidents.insert_many(incidents)

    parts = [
        (\"Battery Module 100kWh\", \"A\"), (\"Traction Inverter 200kW\", \"A\"), (\"Front eAxle\", \"A\"),
        (\"OBC 22kW\", \"B\"), (\"DC-DC Converter\", \"B\"), (\"HV Junction Box\", \"B\"),
        (\"Cooling Pump\", \"C\"), (\"HVAC Compressor\", \"B\"), (\"Wiring Harness — Chassis\", \"B\"),
        (\"BMS Board\", \"A\"), (\"Thermal Plate\", \"C\"), (\"Cell Fuse Assembly\", \"A\"),
    ]
    bom = []
    for name, crit in parts:
        s = random.choice(suppliers)
        bom.append({
            \"id\": str(uuid.uuid4()),
            \"part_name\": name,
            \"part_number\": f\"VC-{random.randint(10000, 99999)}\",
            \"criticality\": crit,
            \"primary_supplier\": s[\"name\"],
            \"unit_cost_usd\": round(random.uniform(48, 12800), 2),
            \"lead_time_days\": s[\"lead_time_days\"],
            \"inventory_days\": random.randint(2, 45),
            \"second_source\": random.random() > 0.4,
        })
    await db.bom.insert_many(bom)
    logger.info(\"Seed complete.\")


@app.on_event(\"startup\")
async def startup():
    await seed_db()


@api.get(\"/\")
async def root():
    return {\"service\": \"Voltcore API\", \"status\": \"ok\"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=[\"*\"],
    allow_headers=[\"*\"],
)


@app.on_event(\"shutdown\")
async def shutdown_db_client():
    client.close()
"
Observation: Overwrite successful: /app/backend/server.py