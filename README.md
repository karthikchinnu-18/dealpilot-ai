# DealPilot AI — The Autonomous Negotiator

> **Autonomous AI Purchasing & Supplier Negotiation Platform**  
> DealPilot AI independently calls suppliers, talks to representatives in their native language (Kannada, Hindi, English, Tamil, Telugu), negotiates for better prices within authorized budget limits, extracts structured quotations, compares deals deterministically, and presents evidence-backed recommendations for mandatory human sign-off.

---

## 🌟 Key Capabilities

1. **Autonomous Voice Calling (Simulated & Real Telephony)**
   - **Simulated Demo Mode**: 100% free offline mode with realistic multilingual supplier personas, dynamic objections, counteroffers, and busy/no-answer failure scenarios.
   - **Real Outbound Calls**: Production-ready Twilio telephony integration with speech recognition, TwiML generation, and webhook security callbacks.
2. **Multilingual Understanding**
   - Independent user interface language and supplier conversation language.
   - Native dialogue support for **Kannada (ಕನ್ನಡ)**, **Hindi (हिन्दी)**, **English**, **Tamil (தமிழ்)**, and **Telugu (తెలుగు)** with in-browser Text-to-Speech (TTS) audio playback.
3. **Transparent Negotiation Strategy Engine**
   - Strictly enforces budget caps and target limits in backend code independent of generative AI hallucinations.
   - Evaluates multi-round trade-offs, progressive counteroffers, and delivery deadlines.
4. **Structured Quotation Extraction & Evidence Ledger**
   - Automatically extracts unit prices, total costs, GST/taxes, shipping, delivery dates, and warranties from audio transcripts.
   - Distinct evidence statuses: `Verified by Documented Check`, `Supplier Stated`, `User Entered`, `Simulated`, and `Disputed`.
5. **Deterministic Comparison & Scoring Engine**
   - Evaluates Cost, Delivery, Quality, Evidence Completeness, and Penalties for missing data.
   - Disqualifies suppliers that fail mandatory constraints (e.g., budget overage or missed deadlines).
6. **Strict Human Oversight & Governance**
   - Prominently displays safety notices: *"Human approval is strictly required before any purchase or binding commitment."*
   - Interactive Approval / Rejection modal with recorded supervisor audit notes and timestamps.
7. **Relational Data Persistence**
   - Backed by SQLAlchemy ORM with zero-config local file SQLite (`dealpilot.db`), easily upgradeable to PostgreSQL via `DATABASE_URL`.

---

## 🏗️ System Architecture

```
dealpilot-ai/
├── backend/
│   ├── app/
│   │   ├── config.py              # Environment configuration & credential checks
│   │   ├── database.py            # SQLAlchemy database engine & session
│   │   ├── models.py              # Relational models: PurchaseRequest, Supplier, CallRecord, Offer, EvidenceRecord, Recommendation
│   │   ├── schemas.py             # Pydantic validation schemas
│   │   ├── main.py                # FastAPI application & router mounting
│   │   ├── routers/
│   │   │   ├── negotiations.py    # Purchase requests, offers, recommendation & approvals
│   │   │   ├── suppliers.py       # Supplier management & phone validation
│   │   │   ├── calls.py           # Outbound batch dispatch (simulated & real)
│   │   │   ├── telephony_webhooks.py # Twilio voice, status, and gather webhooks
│   │   │   └── settings.py        # System health diagnostics & demo reset
│   │   └── services/
│   │       ├── strategy_engine.py # Budget enforcement & multi-round counteroffers
│   │       ├── extraction_engine.py # Structured quote extraction & missing charge flags
│   │       ├── scoring_engine.py  # Transparent deterministic comparison & scoring
│   │       ├── simulation_service.py # Multilingual personas & dialogue simulation
│   │       └── telephony_service.py # Twilio provider abstraction & TwiML builder
│   ├── tests/                     # 11 automated pytest test suites
│   ├── .env.example               # Environment variables template
│   └── requirements.txt           # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.jsx                # Full SaaS workspace with tabbed sections
    │   ├── styles.css             # High-contrast modern SaaS design system
    │   └── utils/speech.js        # Browser Web Speech API TTS helper
    └── package.json               # Frontend dependencies & scripts
```

---

## 🚀 Windows PowerShell Quickstart

### Prerequisites
- **Python 3.12+**
- **Node.js v18+ and npm**

### 1. Backend Setup
Open a PowerShell terminal in the repository root:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Frontend Setup
Open a second PowerShell terminal in the repository root:
```powershell
cd frontend
npm install
npm run dev
```
- Open your browser at: [http://localhost:5173](http://localhost:5173)

### 3. Run Automated Tests
In the backend terminal with `.venv` active:
```powershell
pytest -v
```

---

## ⚙️ Environment Configuration

Copy `backend/.env.example` to `backend/.env`:
```powershell
Copy-Item backend\.env.example backend\.env
```

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./dealpilot.db` |
| `TELEPHONY_PROVIDER` | Provider name (`twilio` or `none`) | `twilio` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID (Optional for simulated demo) | `""` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `""` |
| `TWILIO_PHONE_NUMBER` | Outbound caller ID number | `""` |
| `WEBHOOK_BASE_URL` | Public HTTPS URL for Twilio callbacks (e.g. ngrok) | `""` |
| `OPENAI_API_KEY` | Optional AI Key (Rule-based NLP active by default) | `""` |

---

## ⏱️ 5-Minute Hackathon Demonstration Script

1. **Step 1: Dashboard & System Health**
   - Open [http://localhost:5173](http://localhost:5173).
   - Point out the active **Backend Connected** indicator and the top mode selector set to **Simulated Demo**.
   - Show the prominent compliance notice: *"Human approval is strictly required before any purchase or binding commitment."*

2. **Step 2: Load Sample Purchase Request**
   - Click **Purchase Request** tab.
   - Click **Load Sample Form** to load a realistic order: *100 Cotton T-Shirts, Budget: ₹12,500, Target: ₹10,500, Deadline: 5 days*.
   - Click **Save Request & Proceed to Suppliers**.

3. **Step 3: Supplier Phone Numbers & Validation**
   - Click **Suppliers** tab. Show the 4 loaded suppliers:
     - *Bharat Textiles & Print Works* (Hindi)
     - *Bengaluru Merchandising Hub* (Kannada)
     - *Apex Industrial Supplies* (English)
     - *Metro Print Labs* (English - Busy Line failure scenario)
   - Demonstrate the **Validate** button testing phone number format.

4. **Step 4: Autonomous AI Calls Execution**
   - Click **Start AI Calls**.
   - In the confirmation modal, review the authorization constraints and click **Authorize & Start Calls**.
   - DealPilot AI calls all 4 suppliers simultaneously!

5. **Step 5: Live Call Monitor & Multilingual Dialogue**
   - Switch to **Live Call Monitor**: observe live cards, durations, rounds, and outcomes.
   - Switch to **Call Transcripts**:
     - Point out the **Hindi** conversation with *Bharat Textiles* settling at ₹11,000.
     - Point out the **Kannada (ಕನ್ನಡ)** dialogue with *Bengaluru Merchandising Hub* settling at ₹11,375.
     - Click the **speaker icon (🔊)** to hear the browser speak the dialogue aloud!
     - Point out *Metro Print Labs* properly caught as `NO_ANSWER`.

6. **Step 6: Structured Quotations & Evidence Ledger**
   - Click **Offers & Quotes**: show extracted unit prices, discounts, and delivery dates.
   - Click **Evidence Ledger**: highlight verification statuses (`Simulated`, `Supplier Stated`) and transcript citations.

7. **Step 7: Deterministic Comparison & Final Recommendation**
   - Click **Supplier Comparison**: explain the transparent scoring breakdown (Cost, Delivery, Quality, Penalties).
   - Click **AI Recommendation**: show the top deal banner for *Apex Industrial Supplies* / *Bharat Textiles*.
   - Point out the discount achieved (₹3,250 savings vs baseline).

8. **Step 8: Mandatory Human Approval**
   - Click **Approve Deal**.
   - Enter supervisor notes: *"Price and 3-day delivery approved by purchasing manager."*
   - Click **Confirm Approval**: state transitions to `APPROVED` with audit timestamp!
