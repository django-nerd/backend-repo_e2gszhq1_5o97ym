"""
Database Schemas for SMM Panel

Each Pydantic model maps to a MongoDB collection (lowercased class name).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Admin user for dashboard access
class AdminUser(BaseModel):
    name: str = Field(..., description="Admin full name")
    email: str = Field(..., description="Admin email (login)")
    password_hash: str = Field(..., description="SHA256(password + SECRET)")
    role: Literal["owner", "manager"] = Field("owner", description="Role")
    is_active: bool = Field(True)

# SMM Service definition
class Service(BaseModel):
    name: str = Field(..., description="Service name, e.g., Instagram Followers")
    category: str = Field(..., description="Category, e.g., Instagram, Facebook")
    description: Optional[str] = Field(None)
    rate_per_1k_pkr: float = Field(..., ge=0, description="Price per 1000 units in PKR")
    min: int = Field(10, ge=0)
    max: int = Field(10000, ge=0)
    status: Literal["active", "paused"] = Field("active")

# Order placed by a customer
class Order(BaseModel):
    service_id: str = Field(..., description="ID of service")
    link: str = Field(..., description="Target link/username")
    quantity: int = Field(..., ge=1)
    user_email: Optional[str] = Field(None)
    note: Optional[str] = None
    status: Literal["pending", "processing", "completed", "cancelled"] = Field("pending")
    charge_pkr: float = Field(0, ge=0, description="Calculated charge in PKR")

# Payment records (e.g., JazzCash/Easypaisa)
class Payment(BaseModel):
    user_email: str
    method: Literal["JazzCash", "EasyPaisa", "BankTransfer"]
    amount_pkr: float = Field(..., ge=0)
    reference: Optional[str] = None
    status: Literal["pending", "confirmed", "failed"] = "pending"

# Panel Settings
class PanelSettings(BaseModel):
    panel_name: str = Field("SMM Panel (PK)")
    currency: Literal["PKR"] = "PKR"
    announcement: Optional[str] = None
    payment_methods: List[str] = Field(default_factory=lambda: ["JazzCash", "EasyPaisa"]) 
