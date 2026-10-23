from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import PurchaseRequest, Supplier
from ..schemas import (
    PhoneValidationRequest,
    PhoneValidationResponse,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)
from ..services.telephony_service import TwilioTelephonyProvider

router = APIRouter(prefix="/api", tags=["suppliers"])

@router.post("/suppliers/validate-phone", response_model=PhoneValidationResponse)
def validate_phone(payload: PhoneValidationRequest):
    is_valid, formatted, err = TwilioTelephonyProvider.validate_phone_number(
        country_code=payload.country_code,
        phone=payload.phone_number,
    )
    return PhoneValidationResponse(
        is_valid=is_valid,
        formatted_e164=formatted,
        country_code=payload.country_code,
        national_number=payload.phone_number,
        reason=err if not is_valid else None,
    )

from .calls import execute_call_for_single_supplier

@router.post("/negotiations/{negotiation_id}/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
async def add_supplier(
    negotiation_id: str,
    payload: SupplierCreate,
    db: Session = Depends(get_db),
):
    request = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    is_valid, formatted, _ = TwilioTelephonyProvider.validate_phone_number(
        country_code=payload.country_code,
        phone=payload.phone_number,
    )

    supplier = Supplier(
        negotiation_id=negotiation_id,
        business_name=payload.business_name.strip(),
        country_code=payload.country_code.strip(),
        phone_number=payload.phone_number.strip(),
        contact_person=payload.contact_person or "",
        email=payload.email or "",
        website=payload.website or "",
        notes=payload.notes or "",
        preferred_language=payload.preferred_language or "auto",
        is_valid_phone=is_valid,
        permission_status="authorized",
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    if payload.auto_call:
        await execute_call_for_single_supplier(
            db=db,
            req=request,
            supp=supplier,
            mode=payload.calling_mode,
            user_confirmed=True,
        )

    return supplier

@router.get("/negotiations/{negotiation_id}/suppliers", response_model=List[SupplierOut])
def list_suppliers(negotiation_id: str, db: Session = Depends(get_db)):
    request = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    return db.query(Supplier).filter(Supplier.negotiation_id == negotiation_id).all()

@router.put("/negotiations/{negotiation_id}/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    negotiation_id: str,
    supplier_id: str,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.negotiation_id == negotiation_id,
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "phone_number" in update_data or "country_code" in update_data:
        c_code = update_data.get("country_code", supplier.country_code)
        p_num = update_data.get("phone_number", supplier.phone_number)
        is_valid, _, _ = TwilioTelephonyProvider.validate_phone_number(c_code, p_num)
        supplier.is_valid_phone = is_valid

    for key, value in update_data.items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)
    return supplier

@router.delete("/negotiations/{negotiation_id}/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(negotiation_id: str, supplier_id: str, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.negotiation_id == negotiation_id,
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db.delete(supplier)
    db.commit()
    return None
