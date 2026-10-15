# DealPilot AI — The Negotiator

Hackathon starter for collecting business offers, comparing them, and explaining a recommendation.

## Important
This starter does NOT make real phone calls yet. It provides a local prototype for requirements intake, offer capture, comparison, and evidence-backed recommendations. Real outbound calling needs a configured provider, credentials, authorization, and end-to-end testing.

## Requirements
- Python 3.12+
- Node.js and npm
- VS Code

## Start on Windows
### Backend
Open a terminal in `backend`:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

### Frontend
Open a second terminal in `frontend`:
```powershell
npm install
npm run dev
```
Open the URL Vite prints, normally http://localhost:5173.

## Demo flow
1. Enter product/service, quantity, budget, and deadline.
2. Create a negotiation request.
3. Add offers that were actually obtained, or clearly labelled demo offers.
4. Compare offers by price, delivery, and evidence status.
5. Review the recommendation and its reasons.

## Current limitations
- No real calling provider is connected.
- No AI API is required for this starter.
- Sample offers must never be presented as real quotes.
- Recommendation scoring is a transparent baseline heuristic, not a guarantee.
- Before live calls, add provider integration, caller identification, authorization/consent checks, opt-out handling, and failure-state testing.
