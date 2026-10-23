from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    
    # Check if empty, seed initial sample request & suppliers so frontend is never empty!
    db = SessionLocal()
    try:
        count = db.query(models.PurchaseRequest).count()
        if count == 0:
            req = models.PurchaseRequest(
                product="Premium Screen-Printed Cotton T-Shirts",
                specifications="180 GSM, 100% bio-washed cotton, front 3-color screen print, assorted sizes (M: 40, L: 40, XL: 20)",
                quantity=100,
                unit="units",
                budget=12500.0,
                currency="INR",
                target_price=10500.0,
                max_authorized_price=12500.0,
                deadline="Within 5 days",
                quality_requirements="180 GSM bio-washed combed cotton, non-fading discharge screen print",
                warranty_requirements="Replacement for print peeling or stitching defects",
                return_requirements="30-day replacement on defective garments",
                payment_terms="Net 15 days or 50% advance / 50% on verified delivery",
                delivery_location="Koramangala, Bengaluru, Karnataka 560034",
                mandatory_conditions=["Must deliver within 5 days", "Screen print quality guaranteed"],
                priorities=["best_value", "fastest_delivery"],
                max_negotiation_rounds=3,
                notes="Ready demo dataset prepared for live hackathon presentation.",
                status="READY",
            )
            db.add(req)
            db.flush()

            suppliers_data = [
                {
                    "business_name": "Bharat Textiles & Print Works",
                    "country_code": "+91",
                    "phone_number": "9845012345",
                    "contact_person": "Ramesh Gupta",
                    "preferred_language": "Hindi",
                    "notes": "Large volume screen-printing facility in Surat/Bengaluru.",
                },
                {
                    "business_name": "Bengaluru Merchandising Hub",
                    "country_code": "+91",
                    "phone_number": "9886067890",
                    "contact_person": "Suresh Gowda",
                    "preferred_language": "Kannada",
                    "notes": "Local textile vendor in Chickpet, Bengaluru.",
                },
                {
                    "business_name": "Apex Industrial Supplies",
                    "country_code": "+91",
                    "phone_number": "9900054321",
                    "contact_person": "Anita Sharma",
                    "preferred_language": "English",
                    "notes": "Corporate apparel manufacturer with ISO certification.",
                },
                {
                    "business_name": "Metro Print Labs",
                    "country_code": "+91",
                    "phone_number": "9820011223",
                    "contact_person": "Vikram Patel",
                    "preferred_language": "English",
                    "notes": "Commercial printer (Simulates busy/no-answer scenario).",
                },
            ]

            for s_data in suppliers_data:
                supp = models.Supplier(
                    negotiation_id=req.id,
                    business_name=s_data["business_name"],
                    country_code=s_data["country_code"],
                    phone_number=s_data["phone_number"],
                    contact_person=s_data["contact_person"],
                    preferred_language=s_data["preferred_language"],
                    notes=s_data["notes"],
                    is_valid_phone=True,
                    permission_status="authorized",
                )
                db.add(supp)

            db.commit()
    except Exception as e:
        db.rollback()
        print(f"init_db auto-seed warning: {e}")
    finally:
        db.close()
