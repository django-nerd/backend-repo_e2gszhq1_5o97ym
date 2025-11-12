import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import AdminUser, Service, Order, Payment, PanelSettings

app = FastAPI(title="SMM Panel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class LoginRequest(BaseModel):
    email: str
    password_hash: str

class AuthResponse(BaseModel):
    token: str
    name: str
    role: str

# Admin helpers

def get_admin_by_email(email: str):
    return db.adminuser.find_one({"email": email}) if db else None

# Simple header-based auth: send X-Admin-Token: <email>

def require_admin(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Missing admin token")
    admin = db.adminuser.find_one({"email": x_admin_token})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    if not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin disabled")
    return admin

@app.get("/", tags=["health"]) 
def root():
    return {"message": "SMM Panel API running"}

@app.get("/test", tags=["health"]) 
def test_database():
    info = {
        "backend": "running",
        "database": "connected" if db else "not-configured",
    }
    if db:
        info["collections"] = db.list_collection_names()
    return info

# Auth
@app.post("/api/admin/login", response_model=AuthResponse)
def admin_login(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    admin = db.adminuser.find_one({"email": payload.email})
    if not admin or admin.get("password_hash") != payload.password_hash or not admin.get("is_active", True):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(token=payload.email, name=admin.get("name", "Admin"), role=admin.get("role", "owner"))

# Settings
@app.get("/api/settings", response_model=PanelSettings)
def get_settings():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db.panelsettings.find_one() or {}
    data = {k: doc.get(k) for k in PanelSettings.model_fields.keys() if k in doc}
    return PanelSettings(**data)

@app.post("/api/settings", response_model=PanelSettings)
def update_settings(payload: PanelSettings, admin=Depends(require_admin)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    db.panelsettings.delete_many({})
    db.panelsettings.insert_one(payload.model_dump())
    return payload

# Admin bootstrap
class BootstrapAdmin(BaseModel):
    name: str
    email: str
    password_hash: str

@app.post("/api/admin/bootstrap")
def bootstrap_admin(payload: BootstrapAdmin):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    exists = db.adminuser.find_one({"email": payload.email})
    if exists:
        raise HTTPException(status_code=400, detail="Admin already exists")
    admin = AdminUser(name=payload.name, email=payload.email, password_hash=payload.password_hash, role="owner", is_active=True)
    create_document("adminuser", admin)
    return {"status": "ok"}

# Services
@app.get("/api/services", response_model=List[Service])
def list_services():
    if db is None:
        return []
    docs = get_documents("service")
    return [Service(**{k: d.get(k) for k in Service.model_fields.keys() if k in d}) for d in docs]

@app.post("/api/services", response_model=Service)
def create_service(payload: Service, admin=Depends(require_admin)):
    create_document("service", payload)
    return payload

@app.delete("/api/services/{name}")
def delete_service(name: str, admin=Depends(require_admin)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    res = db.service.delete_one({"name": name})
    return {"deleted": res.deleted_count}

# Orders
@app.post("/api/orders", response_model=Order)
def create_order(payload: Order):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # For simplicity treat service_id as service name
    service = db.service.find_one({"name": payload.service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    rate = float(service.get("rate_per_1k_pkr", 0))
    charge = round((payload.quantity / 1000.0) * rate, 2)
    payload.charge_pkr = charge
    create_document("order", payload)
    return payload

@app.get("/api/orders", response_model=List[Order])
def list_orders(admin=Depends(require_admin)):
    docs = get_documents("order")
    return [Order(**{k: d.get(k) for k in Order.model_fields.keys() if k in d}) for d in docs]

# Payments
@app.post("/api/payments", response_model=Payment)
def create_payment(payload: Payment):
    create_document("payment", payload)
    return payload

@app.get("/api/payments", response_model=List[Payment])
def list_payments(admin=Depends(require_admin)):
    docs = get_documents("payment")
    return [Payment(**{k: d.get(k) for k in Payment.model_fields.keys() if k in d}) for d in docs]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
