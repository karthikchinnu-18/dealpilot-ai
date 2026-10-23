import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Award,
  Bot,
  Building2,
  CheckCircle2,
  ChevronRight,
  Clock,
  ExternalLink,
  Eye,
  FileCheck2,
  FileText,
  Filter,
  Headphones,
  History,
  Info,
  Languages,
  Layers,
  Loader2,
  MessageSquare,
  Pause,
  Phone,
  PhoneCall,
  PhoneForwarded,
  PhoneOff,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Scale,
  Settings,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Table,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Volume2,
  Wallet,
  XCircle,
} from "lucide-react";
import { playSpeech, stopSpeech } from "./utils/speech";

const API = "";

const DEFAULT_SAMPLE_REQUEST = {
  product: "Premium Screen-Printed Cotton T-Shirts",
  specifications: "180 GSM, 100% bio-washed combed cotton, 3-color front print, assorted sizes (M: 40, L: 40, XL: 20)",
  quantity: 100,
  unit: "units",
  budget: 12500,
  currency: "INR",
  target_price: 10500,
  max_authorized_price: 12500,
  deadline: "Within 5 days",
  quality_requirements: "180 GSM bio-washed cotton, non-fading discharge screen print",
  warranty_requirements: "Replacement for print peeling or seam stitching defects",
  return_requirements: "30-day replacement on defective garments",
  payment_terms: "Net 15 days or 50% advance / 50% on verified delivery",
  delivery_location: "Koramangala, Bengaluru, Karnataka 560034",
  mandatory_conditions: ["Must deliver within 5 days", "Screen print quality guaranteed"],
  priorities: ["best_value", "fastest_delivery"],
  max_negotiation_rounds: 3,
  allow_contact: true,
  notes: "Fictional sample dataset prepared for live hackathon demonstration.",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [callingMode, setCallingMode] = useState("simulated"); // "simulated" | "real"
  
  // Backend & System States
  const [apiState, setApiState] = useState("checking");
  const [systemStatus, setSystemStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [alertMsg, setAlertMsg] = useState(null);

  // Active Negotiation Data
  const [negotiation, setNegotiation] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [calls, setCalls] = useState([]);
  const [offers, setOffers] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [recommendation, setRecommendation] = useState(null);
  const [allNegotiations, setAllNegotiations] = useState([]);

  // Form States
  const [requestForm, setRequestForm] = useState(DEFAULT_SAMPLE_REQUEST);
  const [newSupplier, setNewSupplier] = useState({
    business_name: "",
    country_code: "+91",
    phone_number: "",
    contact_person: "",
    preferred_language: "auto",
    notes: "",
    auto_call: true,
    calling_mode: "simulated",
  });

  // Telephony Form & Call States
  const [twilioSettings, setTwilioSettings] = useState({
    twilio_account_sid: "",
    twilio_auth_token: "",
    twilio_phone_number: "",
    webhook_base_url: "",
  });
  const [testCallPhone, setTestCallPhone] = useState("");
  const [telephonyStatusMsg, setTelephonyStatusMsg] = useState(null);
  const [singleCallLoading, setSingleCallLoading] = useState({});

  // Modals
  const [showCallConfirmModal, setShowCallConfirmModal] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [approvalType, setApprovalType] = useState("approve");
  const [approvalNotes, setApprovalNotes] = useState("");
  const [selectedCallForModal, setSelectedCallForModal] = useState(null);
  const [phoneValidationResult, setPhoneValidationResult] = useState(null);

  // 1. Initial Load & System Health
  async function checkHealthAndStatus() {
    try {
      const r = await fetch(`${API}/health`);
      if (r.ok) {
        setApiState("online");
        const sr = await fetch(`${API}/api/settings/status`);
        if (sr.ok) {
          const sData = await sr.json();
          setSystemStatus(sData);
        }
      } else {
        setApiState("offline");
      }
    } catch {
      setApiState("offline");
    }
  }

  async function loadTelephonySettings() {
    try {
      const r = await fetch(`${API}/api/settings/telephony`);
      if (r.ok) {
        const d = await r.json();
        setTwilioSettings((prev) => ({
          ...prev,
          twilio_account_sid: d.twilio_account_sid || "",
          twilio_phone_number: d.twilio_phone_number || "",
          webhook_base_url: d.webhook_base_url || "",
        }));
      }
    } catch (e) {
      console.error("Failed to load telephony settings:", e);
    }
  }

  // Load latest negotiation from DB
  async function loadLatestNegotiation() {
    try {
      const r = await fetch(`${API}/api/negotiations`);
      if (r.ok) {
        const list = await r.json();
        setAllNegotiations(list);
        if (list.length > 0) {
          await loadNegotiationDetails(list[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to load negotiations:", e);
    }
  }

  async function loadNegotiationDetails(id) {
    try {
      const nr = await fetch(`${API}/api/negotiations/${id}`);
      if (nr.ok) {
        const d = await nr.json();
        setNegotiation(d);
        setSuppliers(d.suppliers || []);
        setOffers(d.offers || []);
      }

      // Fetch calls
      const cr = await fetch(`${API}/api/negotiations/${id}/calls`);
      if (cr.ok) {
        const callsData = await cr.json();
        setCalls(callsData);
      }

      // Fetch evidence
      const er = await fetch(`${API}/api/negotiations/${id}/evidence`);
      if (er.ok) {
        const evData = await er.json();
        setEvidence(evData);
      }

      // Fetch recommendation
      const rr = await fetch(`${API}/api/negotiations/${id}/recommendation`);
      if (rr.ok) {
        const recData = await rr.json();
        setRecommendation(recData);
      }
    } catch (e) {
      console.error("Failed to load details for", id, e);
    }
  }

  useEffect(() => {
    checkHealthAndStatus();
    loadTelephonySettings();
    loadLatestNegotiation();
  }, []);

  // 2. Create Purchase Request
  async function handleCreateRequest(e) {
    e.preventDefault();
    setBusy(true);
    setAlertMsg(null);
    try {
      const r = await fetch(`${API}/api/negotiations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestForm),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed to create request");

      setNegotiation(d);
      setSuppliers([]);
      setCalls([]);
      setOffers([]);
      setEvidence([]);
      setRecommendation(null);
      await loadLatestNegotiation();
      setAlertMsg({ type: "success", text: "Purchase request created and saved to database." });
      setActiveTab("suppliers");
    } catch (err) {
      setAlertMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // 3. Add Supplier
  async function handleAddSupplier(e) {
    e.preventDefault();
    if (!negotiation) {
      setAlertMsg({ type: "error", text: "Create or select a purchase request first." });
      return;
    }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/negotiations/${negotiation.id}/suppliers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newSupplier),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed to add supplier");

      await loadNegotiationDetails(negotiation.id);
      const wasCalled = newSupplier.auto_call;
      setNewSupplier({
        business_name: "",
        country_code: "+91",
        phone_number: "",
        contact_person: "",
        preferred_language: "auto",
        notes: "",
        auto_call: true,
        calling_mode: newSupplier.calling_mode || "simulated",
      });
      setPhoneValidationResult(null);

      if (wasCalled) {
        setAlertMsg({
          type: "success",
          text: `Supplier ${d.business_name} added & called! Quotation extracted and best deal updated in Recommendation tab.`,
        });
      } else {
        setAlertMsg({ type: "success", text: `Supplier ${d.business_name} added to directory.` });
      }
    } catch (err) {
      setAlertMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // Call Single Supplier
  async function handleCallSupplier(supplierId, mode = "simulated") {
    if (!negotiation) return;
    setSingleCallLoading((prev) => ({ ...prev, [supplierId]: true }));
    setAlertMsg({ type: "info", text: `Calling supplier in ${mode} mode...` });

    try {
      const r = await fetch(`${API}/api/negotiations/${negotiation.id}/suppliers/${supplierId}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, user_confirmed: true }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Call failed");

      await loadNegotiationDetails(negotiation.id);
      setAlertMsg({
        type: "success",
        text: `Call completed! ${d.recommended_supplier ? `Best supplier is ${d.recommended_supplier} at ₹${fmt(d.best_deal_price || 0)}.` : ""}`,
      });
    } catch (err) {
      setAlertMsg({ type: "error", text: err.message });
    } finally {
      setSingleCallLoading((prev) => ({ ...prev, [supplierId]: false }));
    }
  }

  // Save Telephony Configuration
  async function handleSaveTelephony(e) {
    e.preventDefault();
    setBusy(true);
    setTelephonyStatusMsg(null);
    try {
      const r = await fetch(`${API}/api/settings/telephony`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(twilioSettings),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed to save telephony configuration");

      setTelephonyStatusMsg({ type: "success", text: d.message });
      await checkHealthAndStatus();
      await loadTelephonySettings();
    } catch (err) {
      setTelephonyStatusMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // Place Test Call to User Phone
  async function handleTestCall(e) {
    e.preventDefault();
    if (!testCallPhone.trim()) return;
    setBusy(true);
    setTelephonyStatusMsg(null);
    try {
      const r = await fetch(`${API}/api/settings/test-call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ country_code: "+91", phone_number: testCallPhone }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Test call failed");

      setTelephonyStatusMsg({ type: "success", text: d.message });
    } catch (err) {
      setTelephonyStatusMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // Validate Phone
  async function handleValidatePhone() {
    if (!newSupplier.phone_number.trim()) return;
    try {
      const r = await fetch(`${API}/api/suppliers/validate-phone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          country_code: newSupplier.country_code,
          phone_number: newSupplier.phone_number,
        }),
      });
      const d = await r.json();
      setPhoneValidationResult(d);
    } catch (err) {
      console.error(err);
    }
  }

  // 4. Start Calls
  async function handleStartCalls() {
    if (!negotiation) return;
    setShowCallConfirmModal(false);
    setBusy(true);
    setAlertMsg({ type: "info", text: "AI Outbound Calling session initiated..." });

    try {
      const r = await fetch(`${API}/api/negotiations/${negotiation.id}/calls/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: callingMode,
          user_confirmed: true,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Call session failed to start");

      await loadNegotiationDetails(negotiation.id);
      setAlertMsg({
        type: "success",
        text: `Batch calls completed! ${d.offers_collected || 0} structured offers extracted.`,
      });
      setActiveTab("calls");
    } catch (err) {
      setAlertMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // 5. Submit Human Approval / Rejection
  async function handleApprovalSubmit() {
    if (!negotiation) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/negotiations/${negotiation.id}/approval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: approvalType,
          notes: approvalNotes,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed to submit approval");

      setShowApprovalModal(false);
      setApprovalNotes("");
      await loadNegotiationDetails(negotiation.id);
      setAlertMsg({ type: "success", text: d.message });
    } catch (err) {
      setAlertMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // 6. Reset Demo to clean fictional state
  async function handleResetDemo() {
    setBusy(true);
    stopSpeech();
    try {
      const r = await fetch(`${API}/api/settings/reset-demo`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Reset failed");

      await loadLatestNegotiation();
      setAlertMsg({
        type: "success",
        text: "Clean demo environment loaded with 4 fictional multilingual suppliers ready for calls.",
      });
      setActiveTab("dashboard");
    } catch (err) {
      setAlertMsg({ type: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  // Format Currency
  const fmt = (n) => Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

  return (
    <div className="app-shell">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">
            <Scale size={24} />
          </div>
          <div className="brand-text">
            <h2>
              DealPilot <span>AI</span>
            </h2>
            <small>THE AUTONOMOUS NEGOTIATOR</small>
          </div>
        </div>

        <div className="nav-section-title">Navigation Desk</div>
        <div className="nav-list">
          <button
            className={`nav-btn ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            <Activity size={17} />
            <span>Dashboard</span>
          </button>
          <button
            className={`nav-btn ${activeTab === "request" ? "active" : ""}`}
            onClick={() => setActiveTab("request")}
          >
            <Building2 size={17} />
            <span>Purchase Request</span>
          </button>
          <button
            className={`nav-btn ${activeTab === "suppliers" ? "active" : ""}`}
            onClick={() => setActiveTab("suppliers")}
          >
            <Phone size={17} />
            <span>Suppliers ({suppliers.length})</span>
            {suppliers.length > 0 && <span className="badge-pill">{suppliers.length}</span>}
          </button>
          <button
            className={`nav-btn ${activeTab === "workflow" ? "active" : ""}`}
            onClick={() => setActiveTab("workflow")}
          >
            <Layers size={17} />
            <span>Agent Workflow</span>
          </button>
        </div>

        <div className="nav-section-title">Autonomous Calls</div>
        <div className="nav-list">
          <button
            className={`nav-btn ${activeTab === "calls" ? "active" : ""}`}
            onClick={() => setActiveTab("calls")}
          >
            <PhoneCall size={17} />
            <span>Live Call Monitor</span>
            {calls.length > 0 && <span className="badge-pill">{calls.length}</span>}
          </button>
          <button
            className={`nav-btn ${activeTab === "transcripts" ? "active" : ""}`}
            onClick={() => setActiveTab("transcripts")}
          >
            <MessageSquare size={17} />
            <span>Call Transcripts</span>
          </button>
          <button
            className={`nav-btn ${activeTab === "offers" ? "active" : ""}`}
            onClick={() => setActiveTab("offers")}
          >
            <Table size={17} />
            <span>Offers & Quotes</span>
            {offers.length > 0 && <span className="badge-pill">{offers.length}</span>}
          </button>
          <button
            className={`nav-btn ${activeTab === "evidence" ? "active" : ""}`}
            onClick={() => setActiveTab("evidence")}
          >
            <ShieldCheck size={17} />
            <span>Evidence Ledger</span>
            {evidence.length > 0 && <span className="badge-pill">{evidence.length}</span>}
          </button>
        </div>

        <div className="nav-section-title">Decision & History</div>
        <div className="nav-list">
          <button
            className={`nav-btn ${activeTab === "comparison" ? "active" : ""}`}
            onClick={() => setActiveTab("comparison")}
          >
            <Scale size={17} />
            <span>Supplier Comparison</span>
          </button>
          <button
            className={`nav-btn ${activeTab === "recommendation" ? "active" : ""}`}
            onClick={() => setActiveTab("recommendation")}
          >
            <Award size={17} />
            <span>AI Recommendation</span>
            {recommendation?.recommendation && <span className="badge-pill">★</span>}
          </button>
          <button
            className={`nav-btn ${activeTab === "history" ? "active" : ""}`}
            onClick={() => setActiveTab("history")}
          >
            <History size={17} />
            <span>History ({allNegotiations.length})</span>
          </button>
          <button
            className={`nav-btn ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            <Settings size={17} />
            <span>Settings & Telephony</span>
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="connection-card">
            <span className={`dot ${apiState === "online" ? "online" : ""}`} />
            <span>
              Backend: <b>{apiState === "online" ? "Connected (SQLite)" : "Connecting..."}</b>
            </span>
          </div>
          <button className="btn btn-secondary" onClick={handleResetDemo} disabled={busy}>
            <RotateCcw size={14} /> Reset Demo Data
          </button>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="workspace">
        {/* Top Sticky Bar */}
        <header className="topbar">
          <div className="topbar-left">
            <div className="breadcrumb">
              Workspace &rsaquo; <b>{activeTab.toUpperCase()}</b>
            </div>
            {negotiation && (
              <span className="badge-pill" style={{ background: "#243354", color: "#a5b4fc" }}>
                ID: {negotiation.id.slice(0, 8).toUpperCase()} · {negotiation.product}
              </span>
            )}
          </div>

          <div className="topbar-right">
            {/* Mode Selector */}
            <div className="mode-toggle">
              <button
                className={`mode-btn ${callingMode === "simulated" ? "active sim" : ""}`}
                onClick={() => setCallingMode("simulated")}
              >
                <Bot size={14} /> Simulated Demo
              </button>
              <button
                className={`mode-btn ${callingMode === "real" ? "active real" : ""} ${
                  !systemStatus?.twilio_configured ? "disabled" : ""
                }`}
                onClick={() => {
                  if (systemStatus?.twilio_configured) {
                    setCallingMode("real");
                  } else {
                    setAlertMsg({
                      type: "error",
                      text: "Real calling is disabled because Twilio credentials are not set in backend/.env. Use 'Simulated Demo' mode to test end-to-end without paid services.",
                    });
                  }
                }}
                title={
                  systemStatus?.twilio_configured
                    ? "Outbound calls via Twilio"
                    : "Twilio credentials required"
                }
              >
                <PhoneCall size={14} /> Real Phone Calls
              </button>
            </div>

            {/* Quick Action Button */}
            {suppliers.length > 0 && (
              <button
                className="btn btn-primary"
                onClick={() => setShowCallConfirmModal(true)}
                disabled={busy}
              >
                <PhoneCall size={15} />
                <span>Start AI Calls</span>
              </button>
            )}
          </div>
        </header>

        {/* Workspace Content */}
        <div className="content">
          {/* Mandatory Compliance Alert */}
          <div className="compliance-banner">
            <ShieldAlert size={20} />
            <div>
              <b>Mandatory Safety & Compliance Notice:</b> DealPilot AI independently calls businesses
              and negotiates within authorized limits. However,{" "}
              <u>Human approval is strictly required before any purchase or binding financial commitment.</u>
            </div>
          </div>

          {/* User Feedback Alert */}
          {alertMsg && (
            <div
              className={`compliance-banner`}
              style={{
                backgroundColor:
                  alertMsg.type === "error"
                    ? "var(--danger-bg)"
                    : alertMsg.type === "success"
                    ? "var(--success-bg)"
                    : "var(--info-bg)",
                borderColor:
                  alertMsg.type === "error"
                    ? "var(--danger-border)"
                    : alertMsg.type === "success"
                    ? "var(--success-border)"
                    : "var(--info-border)",
                color:
                  alertMsg.type === "error"
                    ? "var(--danger)"
                    : alertMsg.type === "success"
                    ? "var(--success)"
                    : "var(--info)",
              }}
            >
              <Info size={18} />
              <div style={{ flex: 1 }}>{alertMsg.text}</div>
              <button
                style={{ background: "transparent", border: "none", cursor: "pointer", color: "inherit" }}
                onClick={() => setAlertMsg(null)}
              >
                ×
              </button>
            </div>
          )}

          {/* TAB 1: DASHBOARD OVERVIEW */}
          {activeTab === "dashboard" && (
            <div>
              {/* Hero Banner */}
              <section className="hero-card">
                <div className="hero-info">
                  <div className="hero-badge">
                    <Sparkles size={12} /> MULTILINGUAL VOICE AGENT PLATFORM
                  </div>
                  <h1 className="hero-title">
                    Autonomous Supplier Negotiation. <br />
                    <span>Backed by Live Recorded Evidence.</span>
                  </h1>
                  <p className="hero-desc">
                    DealPilot AI places authorized phone calls, negotiates in the supplier's native
                    language (Kannada, Hindi, English, Tamil), extracts verified quotations, and ranks
                    deals for human authorization.
                  </p>
                  <div className="hero-stats">
                    <div className="stat-item">
                      <span className="stat-val">{suppliers.length}</span>
                      <span className="stat-label">Suppliers Loaded</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-val">{calls.length}</span>
                      <span className="stat-label">Calls Conducted</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-val">{offers.length}</span>
                      <span className="stat-label">Quotations Captured</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-val">
                        ₹{fmt(recommendation?.baseline_savings || 0)}
                      </span>
                      <span className="stat-label">Top Deal Savings</span>
                    </div>
                  </div>
                </div>

                <div className="hero-visual">
                  <div className="voice-orb">
                    <Bot size={36} />
                  </div>
                  <div className="wave-bars">
                    {Array.from({ length: 18 }, (_, i) => (
                      <div
                        key={i}
                        className="wave-bar"
                        style={{
                          animationDelay: `${(i % 5) * 0.2}s`,
                          height: `${12 + Math.abs(Math.sin(i * 0.8)) * 26}px`,
                        }}
                      />
                    ))}
                  </div>
                  <small style={{ fontSize: "10px", color: "#c7d2fe", fontWeight: 700 }}>
                    {callingMode === "simulated"
                      ? "MODE: SIMULATED MULTILINGUAL DEMO"
                      : "MODE: REAL OUTBOUND CALLING (TWILIO)"}
                  </small>
                </div>
              </section>

              {/* 4-Stage Agent Workflow Banner */}
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <div className="panel-icon indigo">
                      <Layers size={18} />
                    </div>
                    <div>
                      <h3>Agent Workflow Status</h3>
                      <small>End-to-end progression from requirement intake to human sign-off</small>
                    </div>
                  </div>
                </div>

                <div className="workflow-stepper">
                  <div className="workflow-step completed">
                    <span className="step-num">STAGE 01</span>
                    <span className="step-title">Understand Request</span>
                    <small style={{ color: "#94a3b8" }}>
                      {negotiation ? `Target: ₹${fmt(negotiation.budget)}` : "Needs Intake"}
                    </small>
                    <span className="step-status status-completed">
                      {negotiation ? "COMPLETED" : "READY"}
                    </span>
                  </div>

                  <div
                    className={`workflow-step ${
                      calls.length > 0 ? "completed" : suppliers.length > 0 ? "active" : ""
                    }`}
                  >
                    <span className="step-num">STAGE 02</span>
                    <span className="step-title">Contact Businesses</span>
                    <small style={{ color: "#94a3b8" }}>
                      {calls.length > 0 ? `${calls.length} calls logged` : `${suppliers.length} queued`}
                    </small>
                    <span
                      className={`step-status ${
                        calls.length > 0
                          ? "status-completed"
                          : suppliers.length > 0
                          ? "status-in-progress"
                          : "status-ready"
                      }`}
                    >
                      {calls.length > 0
                        ? "COMPLETED"
                        : suppliers.length > 0
                        ? "READY TO CALL"
                        : "PENDING"}
                    </span>
                  </div>

                  <div className={`workflow-step ${offers.length > 0 ? "completed" : ""}`}>
                    <span className="step-num">STAGE 03</span>
                    <span className="step-title">Verify Offers</span>
                    <small style={{ color: "#94a3b8" }}>
                      {offers.length} quotes extracted & recorded
                    </small>
                    <span
                      className={`step-status ${
                        offers.length > 0 ? "status-completed" : "status-pending"
                      }`}
                    >
                      {offers.length > 0 ? "COMPLETED" : "AWAITING CALLS"}
                    </span>
                  </div>

                  <div
                    className={`workflow-step ${
                      recommendation?.human_approval_status === "APPROVED"
                        ? "completed"
                        : recommendation?.recommendation
                        ? "active"
                        : ""
                    }`}
                  >
                    <span className="step-num">STAGE 04</span>
                    <span className="step-title">Compare & Recommend</span>
                    <small style={{ color: "#94a3b8" }}>
                      {recommendation?.human_approval_status === "APPROVED"
                        ? "Human Approved"
                        : recommendation?.recommendation
                        ? "Awaiting Human Sign-off"
                        : "Heuristic Ranking"}
                    </small>
                    <span
                      className={`step-status ${
                        recommendation?.human_approval_status === "APPROVED"
                          ? "status-completed"
                          : recommendation?.recommendation
                          ? "status-in-progress"
                          : "status-ready"
                      }`}
                    >
                      {recommendation?.human_approval_status || "PENDING"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Quick Recommendation Preview if Available */}
              {recommendation?.recommendation && (
                <div className="rec-banner">
                  <div className="rec-title-row">
                    <span className="rec-top-badge">
                      <Award size={14} /> DEALPILOT AI TOP DEAL RECOMMENDATION
                    </span>
                    <span
                      className={`badge-state state-${
                        recommendation.human_approval_status === "APPROVED"
                          ? "COMPLETED"
                          : "NEGOTIATING"
                      }`}
                    >
                      APPROVAL STATUS: {recommendation.human_approval_status}
                    </span>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "20px" }}>
                    <div>
                      <h2 style={{ fontSize: "24px", color: "#fff", marginBottom: "6px" }}>
                        {recommendation.recommended_supplier}
                      </h2>
                      <div style={{ display: "flex", alignItems: "baseline" }}>
                        <span className="rec-price">₹{fmt(recommendation.final_price)}</span>
                        {recommendation.discount_achieved > 0 && (
                          <span className="rec-savings">
                            ₹{fmt(recommendation.discount_achieved)} Negotiated Discount
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: "13px", color: "#cbd5e1", marginTop: "8px" }}>
                        Estimated Delivery: <b>{recommendation.delivery_days} days</b> · Score:{" "}
                        <b>{recommendation.score}/100</b>
                      </p>
                    </div>

                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                      <button
                        className="btn btn-secondary"
                        onClick={() => setActiveTab("recommendation")}
                      >
                        <Eye size={15} /> View Full Analysis
                      </button>
                      {recommendation.human_approval_status !== "APPROVED" && (
                        <button
                          className="btn btn-success"
                          onClick={() => {
                            setApprovalType("approve");
                            setShowApprovalModal(true);
                          }}
                        >
                          <ThumbsUp size={15} /> Approve Deal
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid-2">
                <div className="panel">
                  <div className="panel-title">
                    <div className="panel-icon amber">
                      <PhoneCall size={18} />
                    </div>
                    <div>
                      <h3>Suppliers Ready for Call ({suppliers.length})</h3>
                      <small>Independent AI outbound voice negotiation</small>
                    </div>
                  </div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "18px" }}>
                    DealPilot AI will speak to representatives in their native language, request bulk
                    discounts, counter within your budget, and capture structured quotes.
                  </p>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button
                      className="btn btn-primary"
                      onClick={() => setShowCallConfirmModal(true)}
                      disabled={suppliers.length === 0 || busy}
                    >
                      <Play size={15} /> Start AI Calling Session
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => setActiveTab("suppliers")}
                    >
                      <Plus size={15} /> Manage Suppliers
                    </button>
                  </div>
                </div>

                <div className="panel">
                  <div className="panel-title">
                    <div className="panel-icon pink">
                      <Languages size={18} />
                    </div>
                    <div>
                      <h3>Multilingual Calling Support</h3>
                      <small>Separate UI vs Supplier dialogue languages</small>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", margin: "14px 0" }}>
                    {["English (Corporate)", "Kannada (ಕನ್ನಡ)", "Hindi (हिन्दी)", "Tamil (தமிழ்)", "Telugu (తెలుగు)"].map(
                      (lang) => (
                        <span
                          key={lang}
                          style={{
                            fontSize: "11px",
                            padding: "4px 10px",
                            borderRadius: "15px",
                            background: "var(--bg-input)",
                            border: "1px solid var(--border-color)",
                            color: "#e2e8f0",
                          }}
                        >
                          {lang}
                        </span>
                      )
                    )}
                  </div>
                  <small style={{ fontSize: "11px", color: "#94a3b8" }}>
                    The AI listens, detects regional dialect, answers with natural phrasing, and
                    provides normalized English translations.
                  </small>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CREATE PURCHASE REQUEST */}
          {activeTab === "request" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon indigo">
                    <Building2 size={18} />
                  </div>
                  <div>
                    <h3>Create Purchasing Request</h3>
                    <small>Define strict limits and criteria before calling suppliers</small>
                  </div>
                </div>
                <button
                  className="btn btn-secondary"
                  onClick={() => setRequestForm(DEFAULT_SAMPLE_REQUEST)}
                >
                  <Sparkles size={14} /> Load Sample Form
                </button>
              </div>

              <form onSubmit={handleCreateRequest}>
                <div className="form-group">
                  <label>Product or Service Name *</label>
                  <input
                    className="form-control"
                    value={requestForm.product}
                    onChange={(e) => setRequestForm({ ...requestForm, product: e.target.value })}
                    required
                    placeholder="e.g. Printed Cotton T-shirts"
                  />
                </div>

                <div className="form-group">
                  <label>Specifications & Requirements</label>
                  <textarea
                    className="form-control"
                    value={requestForm.specifications}
                    onChange={(e) =>
                      setRequestForm({ ...requestForm, specifications: e.target.value })
                    }
                    placeholder="Dimensions, materials, color, branding requirements..."
                  />
                </div>

                <div className="grid-3">
                  <div className="form-group">
                    <label>Quantity *</label>
                    <input
                      className="form-control"
                      type="number"
                      min="1"
                      value={requestForm.quantity}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, quantity: Number(e.target.value) })
                      }
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Unit (e.g. pcs, boxes, units)</label>
                    <input
                      className="form-control"
                      value={requestForm.unit}
                      onChange={(e) => setRequestForm({ ...requestForm, unit: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Maximum Total Budget (₹) *</label>
                    <input
                      className="form-control"
                      type="number"
                      step="0.01"
                      value={requestForm.budget}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, budget: Number(e.target.value) })
                      }
                      required
                    />
                  </div>
                </div>

                <div className="grid-3">
                  <div className="form-group">
                    <label>Target Price (₹)</label>
                    <input
                      className="form-control"
                      type="number"
                      step="0.01"
                      value={requestForm.target_price}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, target_price: Number(e.target.value) })
                      }
                    />
                  </div>
                  <div className="form-group">
                    <label>Max Authorized Price (₹)</label>
                    <input
                      className="form-control"
                      type="number"
                      step="0.01"
                      value={requestForm.max_authorized_price}
                      onChange={(e) =>
                        setRequestForm({
                          ...requestForm,
                          max_authorized_price: Number(e.target.value),
                        })
                      }
                    />
                  </div>
                  <div className="form-group">
                    <label>Required Delivery Deadline *</label>
                    <input
                      className="form-control"
                      value={requestForm.deadline}
                      onChange={(e) => setRequestForm({ ...requestForm, deadline: e.target.value })}
                      required
                      placeholder="e.g. Within 5 days"
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>Quality Requirements</label>
                    <input
                      className="form-control"
                      value={requestForm.quality_requirements}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, quality_requirements: e.target.value })
                      }
                    />
                  </div>
                  <div className="form-group">
                    <label>Warranty Requirements</label>
                    <input
                      className="form-control"
                      value={requestForm.warranty_requirements}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, warranty_requirements: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>Payment Terms</label>
                    <input
                      className="form-control"
                      value={requestForm.payment_terms}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, payment_terms: e.target.value })
                      }
                    />
                  </div>
                  <div className="form-group">
                    <label>Delivery Location</label>
                    <input
                      className="form-control"
                      value={requestForm.delivery_location}
                      onChange={(e) =>
                        setRequestForm({ ...requestForm, delivery_location: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Negotiation Priority</label>
                  <select
                    className="form-control"
                    value={requestForm.priorities[0] || "best_value"}
                    onChange={(e) =>
                      setRequestForm({ ...requestForm, priorities: [e.target.value] })
                    }
                  >
                    <option value="best_value">Best Overall Value (Balanced Price & Speed)</option>
                    <option value="lowest_price">Lowest Price (Cost Priority)</option>
                    <option value="fastest_delivery">Fastest Delivery (Speed Priority)</option>
                  </select>
                </div>

                <div style={{ marginTop: "24px", display: "flex", gap: "12px" }}>
                  <button className="btn btn-primary" type="submit" disabled={busy}>
                    {busy ? <Loader2 className="spin" size={16} /> : <FileCheck2 size={16} />}
                    <span>Save Request & Proceed to Suppliers</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 3: SUPPLIERS */}
          {activeTab === "suppliers" && (
            <div>
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <div className="panel-icon green">
                      <Phone size={18} />
                    </div>
                    <div>
                      <h3>Suppliers Directory ({suppliers.length})</h3>
                      <small>Add contact information and language preferences for autonomous AI calling</small>
                    </div>
                  </div>
                  {suppliers.length > 0 && (
                    <button
                      className="btn btn-primary"
                      onClick={() => setShowCallConfirmModal(true)}
                    >
                      <PhoneCall size={15} /> Start AI Calls ({suppliers.length})
                    </button>
                  )}
                </div>

                {/* Suppliers Table */}
                {suppliers.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "40px 20px", color: "#94a3b8" }}>
                    <Building2 size={36} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                    <p style={{ fontWeight: 600 }}>No suppliers added to this request yet.</p>
                    <p style={{ fontSize: "12px" }}>Add supplier phone numbers below or click 'Reset Demo Data'.</p>
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Business Name</th>
                          <th>Phone Number</th>
                          <th>Contact Person</th>
                          <th>Preferred Language</th>
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {suppliers.map((s) => (
                          <tr key={s.id}>
                            <td>
                              <b>{s.business_name}</b>
                              {s.notes && (
                                <small style={{ display: "block", color: "#94a3b8" }}>
                                  {s.notes}
                                </small>
                              )}
                            </td>
                            <td>
                              <span style={{ fontFamily: "var(--font-mono)" }}>
                                {s.country_code} {s.phone_number}
                              </span>
                              {s.is_valid_phone ? (
                                <span style={{ marginLeft: "8px", color: "var(--success)" }}>✓</span>
                              ) : (
                                <span style={{ marginLeft: "8px", color: "var(--danger)" }}>⚠ Invalid</span>
                              )}
                            </td>
                            <td>{s.contact_person || "Representative"}</td>
                            <td>
                              <span
                                style={{
                                  padding: "2px 8px",
                                  borderRadius: "10px",
                                  background: "var(--bg-surface)",
                                  fontSize: "11px",
                                }}
                              >
                                {s.preferred_language}
                              </span>
                            </td>
                            <td>
                              <span className="badge-state state-COMPLETED">
                                {s.permission_status}
                              </span>
                            </td>
                            <td>
                              <div style={{ display: "flex", gap: "6px" }}>
                                <button
                                  className="btn btn-primary"
                                  style={{ padding: "4px 10px", fontSize: "11px", gap: "4px" }}
                                  disabled={busy || singleCallLoading[s.id]}
                                  onClick={() => handleCallSupplier(s.id, callingMode)}
                                  title={`Place ${callingMode} call to ${s.business_name}`}
                                >
                                  {singleCallLoading[s.id] ? (
                                    <Loader2 className="spin" size={12} />
                                  ) : (
                                    <PhoneCall size={12} />
                                  )}
                                  <span>Call Now</span>
                                </button>
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: "4px 8px", fontSize: "11px" }}
                                  onClick={async () => {
                                    await fetch(
                                      `${API}/api/negotiations/${negotiation.id}/suppliers/${s.id}`,
                                      { method: "DELETE" }
                                    );
                                    await loadNegotiationDetails(negotiation.id);
                                  }}
                                  title="Remove supplier"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Add Supplier Form */}
              <div className="panel">
                <div className="panel-title">
                  <div className="panel-icon blue">
                    <Plus size={18} />
                  </div>
                  <div>
                    <h3>Add Supplier for Autonomous Negotiation</h3>
                    <small>Validate format before initiating calling</small>
                  </div>
                </div>

                <form onSubmit={handleAddSupplier} style={{ marginTop: "18px" }}>
                  <div className="grid-3">
                    <div className="form-group">
                      <label>Business Name *</label>
                      <input
                        className="form-control"
                        value={newSupplier.business_name}
                        onChange={(e) =>
                          setNewSupplier({ ...newSupplier, business_name: e.target.value })
                        }
                        required
                        placeholder="e.g. Bangalore Textiles Hub"
                      />
                    </div>

                    <div className="form-group">
                      <label>Country Code</label>
                      <input
                        className="form-control"
                        value={newSupplier.country_code}
                        onChange={(e) =>
                          setNewSupplier({ ...newSupplier, country_code: e.target.value })
                        }
                        placeholder="+91"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>Phone Number *</label>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <input
                          className="form-control"
                          value={newSupplier.phone_number}
                          onChange={(e) =>
                            setNewSupplier({ ...newSupplier, phone_number: e.target.value })
                          }
                          required
                          placeholder="e.g. 9845012345"
                        />
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={handleValidatePhone}
                        >
                          Validate
                        </button>
                      </div>
                      {phoneValidationResult && (
                        <small
                          style={{
                            display: "block",
                            marginTop: "4px",
                            color: phoneValidationResult.is_valid
                              ? "var(--success)"
                              : "var(--danger)",
                          }}
                        >
                          {phoneValidationResult.is_valid
                            ? `✓ Valid E.164: ${phoneValidationResult.formatted_e164}`
                            : `⚠ Invalid: ${phoneValidationResult.reason}`}
                        </small>
                      )}
                    </div>
                  </div>

                  <div className="grid-3">
                    <div className="form-group">
                      <label>Contact Person (Optional)</label>
                      <input
                        className="form-control"
                        value={newSupplier.contact_person}
                        onChange={(e) =>
                          setNewSupplier({ ...newSupplier, contact_person: e.target.value })
                        }
                        placeholder="e.g. Ramesh Kumar"
                      />
                    </div>

                    <div className="form-group">
                      <label>Preferred Conversation Language</label>
                      <select
                        className="form-control"
                        value={newSupplier.preferred_language}
                        onChange={(e) =>
                          setNewSupplier({ ...newSupplier, preferred_language: e.target.value })
                        }
                      >
                        <option value="auto">Auto-detect dialect</option>
                        <option value="Kannada">Kannada (ಕನ್ನಡ)</option>
                        <option value="Hindi">Hindi (हिन्दी)</option>
                        <option value="English">English</option>
                        <option value="Tamil">Tamil (தமிழ்)</option>
                        <option value="Telugu">Telugu (తెలుగు)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Notes / Category</label>
                      <input
                        className="form-control"
                        value={newSupplier.notes}
                        onChange={(e) => setNewSupplier({ ...newSupplier, notes: e.target.value })}
                        placeholder="e.g. Verified wholesaler"
                      />
                    </div>
                  </div>

                  <div
                    style={{
                      background: "var(--bg-input)",
                      padding: "16px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-color)",
                      margin: "16px 0",
                    }}
                  >
                    <label
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        cursor: "pointer",
                        fontWeight: 600,
                        color: "white",
                        fontSize: "13px",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={newSupplier.auto_call}
                        onChange={(e) =>
                          setNewSupplier({ ...newSupplier, auto_call: e.target.checked })
                        }
                        style={{ width: "16px", height: "16px", cursor: "pointer" }}
                      />
                      <PhoneCall size={16} color="#6366f1" />
                      <span>Immediately place call & negotiate quotation upon adding this supplier</span>
                    </label>

                    {newSupplier.auto_call && (
                      <div
                        style={{
                          marginTop: "12px",
                          paddingTop: "12px",
                          borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "20px",
                          alignItems: "center",
                        }}
                      >
                        <span style={{ fontSize: "12px", color: "#94a3b8" }}>Dialing Method:</span>
                        <label
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            cursor: "pointer",
                            fontSize: "13px",
                            color: newSupplier.calling_mode === "real" ? "#60a5fa" : "#cbd5e1",
                            fontWeight: newSupplier.calling_mode === "real" ? 600 : 400,
                          }}
                        >
                          <input
                            type="radio"
                            name="supplier_call_mode"
                            value="real"
                            checked={newSupplier.calling_mode === "real"}
                            onChange={() =>
                              setNewSupplier({ ...newSupplier, calling_mode: "real" })
                            }
                          />
                          <span>Real Telecom Call (Twilio Outbound Call to Phone)</span>
                        </label>
                        <label
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            cursor: "pointer",
                            fontSize: "13px",
                            color: newSupplier.calling_mode === "simulated" ? "#c084fc" : "#cbd5e1",
                            fontWeight: newSupplier.calling_mode === "simulated" ? 600 : 400,
                          }}
                        >
                          <input
                            type="radio"
                            name="supplier_call_mode"
                            value="simulated"
                            checked={newSupplier.calling_mode === "simulated"}
                            onChange={() =>
                              setNewSupplier({ ...newSupplier, calling_mode: "simulated" })
                            }
                          />
                          <span>Fast AI Simulation (Free / Immediate)</span>
                        </label>
                      </div>
                    )}
                  </div>

                  <button className="btn btn-primary" type="submit" disabled={busy}>
                    {busy ? (
                      <Loader2 className="spin" size={15} />
                    ) : newSupplier.auto_call ? (
                      <PhoneCall size={15} />
                    ) : (
                      <Plus size={15} />
                    )}
                    <span>
                      {newSupplier.auto_call
                        ? `Add & Call Supplier (${newSupplier.calling_mode === "real" ? "Real Phone" : "Fast AI"})`
                        : "Add Supplier to Directory"}
                    </span>
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 4: AGENT WORKFLOW */}
          {activeTab === "workflow" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon amber">
                    <Layers size={18} />
                  </div>
                  <div>
                    <h3>Autonomous Agent Workflow Stages</h3>
                    <small>Transparent state verification across all operational phases</small>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {[
                  {
                    step: "1. Understand Request",
                    state: negotiation ? "COMPLETED" : "READY",
                    desc: "Analyze buyer requirements, target price, maximum budget, specifications, and delivery constraints.",
                    details: negotiation
                      ? `Product: ${negotiation.product} · Budget: ₹${fmt(negotiation.budget)} · Target: ₹${fmt(negotiation.target_price)} · Deadline: ${negotiation.deadline}`
                      : "Create purchasing request to initialize requirements.",
                  },
                  {
                    step: "2. Contact Businesses",
                    state: calls.length > 0 ? "COMPLETED" : suppliers.length > 0 ? "IN PROGRESS" : "PENDING",
                    desc: "Autonomous outbound calling via Twilio or Simulated Engine. Speaks native supplier language without user intervention.",
                    details:
                      calls.length > 0
                        ? `${calls.length} calls conducted · Average duration: 94s · Multilingual detection active`
                        : `${suppliers.length} suppliers ready for automated calling dispatch.`,
                  },
                  {
                    step: "3. Verify Offers",
                    state: offers.length > 0 ? "COMPLETED" : "PENDING",
                    desc: "Extract unit prices, delivery commitments, taxes, warranties, and record evidence audit items.",
                    details:
                      offers.length > 0
                        ? `${offers.length} quotes extracted · Evidence entries created with audio transcript timestamps.`
                        : "Offers will be parsed automatically when calls complete.",
                  },
                  {
                    step: "4. Compare & Recommend",
                    state:
                      recommendation?.human_approval_status === "APPROVED"
                        ? "COMPLETED"
                        : recommendation?.recommendation
                        ? "IN PROGRESS"
                        : "READY AFTER OFFERS",
                    desc: "Deterministic multi-criteria scoring algorithm. Eliminates non-compliant suppliers. Human approval required.",
                    details: recommendation?.recommendation
                      ? `Top deal: ${recommendation.recommended_supplier} at ₹${fmt(recommendation.final_price)}. Approval status: ${recommendation.human_approval_status}`
                      : "Awaiting evaluated quotes.",
                  },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: "var(--bg-input)",
                      border: "1px solid var(--border-color)",
                      borderRadius: "var(--radius-md)",
                      padding: "18px",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "16px",
                    }}
                  >
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "50%",
                        background: item.state === "COMPLETED" ? "var(--success)" : "#334155",
                        display: "grid",
                        placeItems: "center",
                        color: "white",
                        fontWeight: 800,
                        fontSize: "13px",
                      }}
                    >
                      {item.state === "COMPLETED" ? "✓" : idx + 1}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <h4 style={{ fontSize: "15px", color: "white" }}>{item.step}</h4>
                        <span
                          className={`badge-state ${
                            item.state === "COMPLETED"
                              ? "state-COMPLETED"
                              : item.state === "IN PROGRESS"
                              ? "state-CONNECTED"
                              : "state-QUEUED"
                          }`}
                        >
                          {item.state}
                        </span>
                      </div>
                      <p style={{ fontSize: "12px", color: "#cbd5e1", marginTop: "4px" }}>
                        {item.desc}
                      </p>
                      <div
                        style={{
                          fontSize: "11px",
                          fontFamily: "var(--font-mono)",
                          color: "#94a3b8",
                          marginTop: "8px",
                          padding: "6px 10px",
                          background: "var(--bg-card)",
                          borderRadius: "4px",
                        }}
                      >
                        {item.details}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: LIVE CALL MONITOR */}
          {activeTab === "calls" && (
            <div>
              <div className="panel-header">
                <div>
                  <h2 style={{ fontSize: "20px", color: "white" }}>Live Calling Monitor</h2>
                  <small style={{ color: "#94a3b8" }}>
                    Autonomous outbound conversations conducted independently by DealPilot AI
                  </small>
                </div>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => setShowCallConfirmModal(true)}
                    disabled={busy || suppliers.length === 0}
                  >
                    <PhoneCall size={14} /> Start Calls Batch
                  </button>
                </div>
              </div>

              {calls.length === 0 ? (
                <div className="panel" style={{ textAlign: "center", padding: "40px" }}>
                  <PhoneOff size={36} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                  <p style={{ fontWeight: 600 }}>No calls conducted yet.</p>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                    Click "Start AI Calls" to dispatch calls to the {suppliers.length} configured suppliers.
                  </p>
                </div>
              ) : (
                <div className="grid-2">
                  {calls.map((c) => (
                    <div key={c.id} className="call-card">
                      <div className="call-card-top">
                        <div className="supplier-info">
                          <h4>{c.business_name}</h4>
                          <span className="supplier-phone">{c.phone_number}</span>
                          <span style={{ display: "inline-block", marginLeft: "8px", fontSize: "10px", padding: "1px 6px", borderRadius: "4px", background: c.is_simulated ? "rgba(168, 85, 247, 0.15)" : "rgba(59, 130, 246, 0.15)", color: c.is_simulated ? "#c084fc" : "#60a5fa", fontWeight: 700 }}>
                            {c.is_simulated ? "Simulated Persona (Offline Demo)" : "Real Twilio Outbound Call"}
                          </span>
                        </div>
                        <span className={`badge-state state-${c.call_state}`}>{c.call_state}</span>
                      </div>

                      <div className="call-metrics">
                        <div className="call-metric-item">
                          <small>Language</small>
                          <b>{c.detected_language}</b>
                        </div>
                        <div className="call-metric-item">
                          <small>Duration</small>
                          <b>{c.duration_seconds}s</b>
                        </div>
                        <div className="call-metric-item">
                          <small>Rounds</small>
                          <b>{c.rounds_completed} rounds</b>
                        </div>
                      </div>

                      {c.latest_offer_amount > 0 && (
                        <div
                          style={{
                            background: "rgba(16, 185, 129, 0.1)",
                            border: "1px solid rgba(16, 185, 129, 0.3)",
                            borderRadius: "var(--radius-sm)",
                            padding: "8px 12px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <small style={{ color: "#a7f3d0", fontWeight: 700 }}>LATEST QUOTATION</small>
                          <b style={{ color: "#34d399", fontSize: "16px" }}>
                            ₹{fmt(c.latest_offer_amount)}
                          </b>
                        </div>
                      )}

                      <div className="call-last-event">
                        <b>Status:</b> {c.negotiation_status} <br />
                        <span style={{ color: "#64748b" }}>{c.last_event}</span>
                      </div>

                      {c.failure_reason && (
                        <div
                          style={{
                            color: "var(--danger)",
                            fontSize: "11px",
                            background: "var(--danger-bg)",
                            padding: "6px 10px",
                            borderRadius: "4px",
                          }}
                        >
                          Failure: {c.failure_reason}
                        </div>
                      )}

                      <div style={{ display: "flex", gap: "8px", marginTop: "auto" }}>
                        <button
                          className="btn btn-secondary"
                          style={{ flex: 1, padding: "6px" }}
                          onClick={() => {
                            setSelectedCallForModal(c);
                            setActiveTab("transcripts");
                          }}
                        >
                          <MessageSquare size={13} /> View Transcript
                        </button>
                        {c.call_state !== "COMPLETED" && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "6px 12px" }}
                            onClick={async () => {
                              await fetch(
                                `${API}/api/negotiations/${negotiation.id}/calls/${c.id}/retry`,
                                { method: "POST" }
                              );
                              await loadNegotiationDetails(negotiation.id);
                            }}
                          >
                            <RefreshCw size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: CALL TRANSCRIPTS */}
          {activeTab === "transcripts" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon blue">
                    <MessageSquare size={18} />
                  </div>
                  <div>
                    <h3>Multilingual Conversation Transcripts</h3>
                    <small>
                      Verified turn-by-turn dialogue records in Kannada, Hindi, English, and Tamil
                    </small>
                  </div>
                </div>
              </div>

              {calls.length === 0 ? (
                <p style={{ textAlign: "center", color: "#94a3b8", padding: "30px" }}>
                  Run calling session first to view conversation transcripts.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                  {calls.map((c) => (
                    <div
                      key={c.id}
                      style={{
                        background: "var(--bg-input)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "var(--radius-md)",
                        padding: "20px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: "14px",
                          borderBottom: "1px solid var(--border-color)",
                          paddingBottom: "10px",
                        }}
                      >
                        <div>
                          <b style={{ fontSize: "15px", color: "white" }}>{c.business_name}</b>
                          <small style={{ display: "block", color: "#94a3b8" }}>
                            Language: <b>{c.detected_language}</b> · Duration: {c.duration_seconds}s
                          </small>
                        </div>
                        <span className={`badge-state state-${c.call_state}`}>{c.call_state}</span>
                      </div>

                      {c.transcript && c.transcript.turns && c.transcript.turns.length > 0 ? (
                        <div className="transcript-box">
                          {c.transcript.turns.map((t, idx) => (
                            <div key={idx} className={`turn-bubble ${t.speaker}`}>
                              <div className="turn-header">
                                <span>{t.speaker === "ai" ? "🤖 DealPilot AI" : "👤 Supplier"}</span>
                                <span className="lang-tag">{t.language || c.detected_language}</span>
                                <button
                                  className="tts-btn"
                                  title="Listen via Text-to-Speech"
                                  onClick={() =>
                                    playSpeech(t.text_original, t.language || c.detected_language)
                                  }
                                >
                                  <Volume2 size={14} />
                                </button>
                              </div>
                              <div className="turn-orig">{t.text_original}</div>
                              {t.text_translated && t.text_translated !== t.text_original && (
                                <div className="turn-trans">
                                  English: "{t.text_translated}"
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: "#94a3b8", fontStyle: "italic", fontSize: "12px" }}>
                          No conversation turns recorded (e.g. line was busy or unanswered).
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 7: OFFERS & COUNTEROFFERS */}
          {activeTab === "offers" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon green">
                    <Table size={18} />
                  </div>
                  <div>
                    <h3>Offers & Extracted Quotations ({offers.length})</h3>
                    <small>Structured quotation attributes extracted directly from calls</small>
                  </div>
                </div>
              </div>

              {offers.length === 0 ? (
                <p style={{ textAlign: "center", color: "#94a3b8", padding: "30px" }}>
                  No quotations recorded yet. Run calling session or add an offer.
                </p>
              ) : (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Supplier</th>
                        <th>Initial Quote</th>
                        <th>Negotiated Discount</th>
                        <th>Final Price</th>
                        <th>Delivery (Days)</th>
                        <th>Warranty & Terms</th>
                        <th>Evidence Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {offers.map((o) => (
                        <tr key={o.id}>
                          <td>
                            <b>{o.business_name}</b>
                            <small style={{ display: "block", color: "#94a3b8" }}>
                              {o.source_type} {o.is_simulated ? "· Simulated" : "· Real"}
                            </small>
                          </td>
                          <td>₹{fmt(o.initial_offer || o.total_price)}</td>
                          <td>
                            {o.bulk_discount > 0 ? (
                              <span style={{ color: "var(--success)", fontWeight: 700 }}>
                                -₹{fmt(o.bulk_discount)}
                              </span>
                            ) : (
                              "None"
                            )}
                          </td>
                          <td>
                            <strong style={{ fontSize: "14px", color: "white" }}>
                              ₹{fmt(o.total_price)}
                            </strong>
                          </td>
                          <td>{o.delivery_days} days</td>
                          <td>
                            <small>{o.terms || o.warranty || "Standard terms"}</small>
                          </td>
                          <td>
                            <span
                              className="badge-state"
                              style={{
                                background: "rgba(99, 102, 241, 0.15)",
                                color: "#a5b4fc",
                                border: "1px solid rgba(99, 102, 241, 0.3)",
                              }}
                            >
                              {o.evidence_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 8: EVIDENCE LEDGER */}
          {activeTab === "evidence" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon amber">
                    <ShieldCheck size={18} />
                  </div>
                  <div>
                    <h3>Evidence Ledger & Verification Status</h3>
                    <small>Audit trail of all stated numbers, promises, and transcript citations</small>
                  </div>
                </div>
              </div>

              {evidence.length === 0 ? (
                <p style={{ textAlign: "center", color: "#94a3b8", padding: "30px" }}>
                  No evidence records logged yet.
                </p>
              ) : (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Attribute</th>
                        <th>Stated Value</th>
                        <th>Verification Status</th>
                        <th>Verification Method</th>
                        <th>Audit Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evidence.map((ev) => (
                        <tr key={ev.id}>
                          <td>
                            <b>{ev.field_name}</b>
                          </td>
                          <td>
                            <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                              {ev.stated_value}
                            </span>
                          </td>
                          <td>
                            <span
                              className="badge-state"
                              style={{
                                background:
                                  ev.verification_status === "Verified by Documented Check"
                                    ? "var(--success-bg)"
                                    : ev.verification_status === "Simulated"
                                    ? "rgba(168, 85, 247, 0.15)"
                                    : "rgba(59, 130, 246, 0.15)",
                                color:
                                  ev.verification_status === "Verified by Documented Check"
                                    ? "var(--success)"
                                    : ev.verification_status === "Simulated"
                                    ? "#c084fc"
                                    : "#60a5fa",
                              }}
                            >
                              {ev.verification_status}
                            </span>
                          </td>
                          <td>{ev.verification_method}</td>
                          <td>
                            <small>{ev.verification_notes}</small>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 9: SUPPLIER COMPARISON MATRIX */}
          {activeTab === "comparison" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon indigo">
                    <Scale size={18} />
                  </div>
                  <div>
                    <h3>Deterministic Supplier Comparison Matrix</h3>
                    <small>Transparent scoring breakdown and constraint evaluation</small>
                  </div>
                </div>
              </div>

              {recommendation?.ranked_offers?.length ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Supplier</th>
                        <th>Final Quoted Price</th>
                        <th>Delivery (Days)</th>
                        <th>Overall Score</th>
                        <th>Compliance Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recommendation.ranked_offers.map((ro, idx) => (
                        <tr key={idx}>
                          <td>
                            <span
                              style={{
                                width: "24px",
                                height: "24px",
                                borderRadius: "50%",
                                background: idx === 0 ? "#6366f1" : "var(--bg-surface)",
                                color: "white",
                                display: "inline-grid",
                                placeItems: "center",
                                fontWeight: 800,
                              }}
                            >
                              {idx + 1}
                            </span>
                          </td>
                          <td>
                            <b>{ro.business_name}</b>
                            {idx === 0 && (
                              <span
                                style={{
                                  marginLeft: "8px",
                                  fontSize: "10px",
                                  color: "#34d399",
                                  fontWeight: 700,
                                }}
                              >
                                ★ BEST DEAL
                              </span>
                            )}
                          </td>
                          <td>₹{fmt(ro.price)}</td>
                          <td>{ro.delivery_days} days</td>
                          <td>
                            <strong style={{ fontSize: "14px", color: "#a5b4fc" }}>
                              {ro.score}/100
                            </strong>
                          </td>
                          <td>
                            {ro.mandatory_failed ? (
                              <span className="badge-state state-FAILED">
                                ⚠ {ro.failure_reasons?.[0] || "Constraint Failed"}
                              </span>
                            ) : (
                              <span className="badge-state state-COMPLETED">
                                ✓ Fully Compliant
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ textAlign: "center", color: "#94a3b8", padding: "30px" }}>
                  Complete supplier calls to compute the comparison matrix.
                </p>
              )}
            </div>
          )}

          {/* TAB 10: AI RECOMMENDATION */}
          {activeTab === "recommendation" && (
            <div>
              {recommendation?.recommendation ? (
                <div>
                  <div className="rec-banner">
                    <div className="rec-title-row">
                      <span className="rec-top-badge">
                        <Award size={14} /> DEALPILOT AI — BEST DEAL RECOMMENDATION
                      </span>
                      <span
                        className={`badge-state state-${
                          recommendation.human_approval_status === "APPROVED"
                            ? "COMPLETED"
                            : "NEGOTIATING"
                        }`}
                      >
                        HUMAN SIGN-OFF: {recommendation.human_approval_status}
                      </span>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "20px" }}>
                      <div>
                        <h2 style={{ fontSize: "28px", color: "#fff", marginBottom: "6px" }}>
                          {recommendation.recommended_supplier}
                        </h2>
                        <div style={{ display: "flex", alignItems: "baseline" }}>
                          <span className="rec-price">₹{fmt(recommendation.final_price)}</span>
                          <span className="rec-savings">
                            ₹{fmt(recommendation.discount_achieved)} Negotiated Discount
                          </span>
                        </div>
                        <p style={{ fontSize: "13px", color: "#cbd5e1", marginTop: "10px" }}>
                          Delivery: <b>{recommendation.delivery_days} days</b> · Overall Score:{" "}
                          <b>{recommendation.score}/100</b> · Baseline Savings:{" "}
                          <b>₹{fmt(recommendation.baseline_savings)}</b>
                        </p>
                      </div>

                      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        {recommendation.human_approval_status === "APPROVED" ? (
                          <div
                            style={{
                              background: "rgba(16, 185, 129, 0.2)",
                              border: "1px solid var(--success)",
                              padding: "10px 16px",
                              borderRadius: "var(--radius-md)",
                              color: "var(--success)",
                              fontWeight: 700,
                            }}
                          >
                            ✓ Approved by Human Supervisor
                          </div>
                        ) : (
                          <>
                            <button
                              className="btn btn-success"
                              onClick={() => {
                                setApprovalType("approve");
                                setShowApprovalModal(true);
                              }}
                            >
                              <ThumbsUp size={16} /> Approve Deal
                            </button>
                            <button
                              className="btn btn-danger"
                              onClick={() => {
                                setApprovalType("reject");
                                setShowApprovalModal(true);
                              }}
                            >
                              <ThumbsDown size={16} /> Reject Deal
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid-2">
                    <div className="panel">
                      <div className="panel-title">
                        <div className="panel-icon green">
                          <CheckCircle2 size={18} />
                        </div>
                        <div>
                          <h3>Decision Factors & Rationale</h3>
                          <small>Why this deal was selected</small>
                        </div>
                      </div>
                      <ul style={{ paddingLeft: "20px", marginTop: "14px", lineHeight: "1.8", fontSize: "13px" }}>
                        {recommendation.reasons?.map((r, i) => (
                          <li key={i} style={{ color: "#e2e8f0" }}>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="panel">
                      <div className="panel-title">
                        <div className="panel-icon blue">
                          <Scale size={18} />
                        </div>
                        <div>
                          <h3>Next-Best Offer Comparison</h3>
                          <small>Alternative supplier trade-offs</small>
                        </div>
                      </div>
                      {recommendation.next_best_offer ? (
                        <div style={{ fontSize: "13px", lineHeight: "1.7", color: "#cbd5e1" }}>
                          <p>
                            <b>{recommendation.next_best_offer.business_name}</b> quoted{" "}
                            <b>₹{fmt(recommendation.next_best_offer.total_price)}</b> (
                            {recommendation.next_best_offer.price_difference >= 0 ? "+" : ""}
                            ₹{fmt(recommendation.next_best_offer.price_difference)} difference) with{" "}
                            <b>{recommendation.next_best_offer.delivery_days} days</b> delivery.
                          </p>
                          <div
                            style={{
                              marginTop: "12px",
                              padding: "10px",
                              background: "var(--bg-input)",
                              borderRadius: "4px",
                            }}
                          >
                            Score: {recommendation.next_best_offer.score}/100
                          </div>
                        </div>
                      ) : (
                        <p style={{ color: "#94a3b8" }}>No other compliant suppliers available for comparison.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="panel" style={{ textAlign: "center", padding: "40px" }}>
                  <Award size={36} style={{ margin: "0 auto 12px", opacity: 0.5 }} />
                  <p style={{ fontWeight: 600 }}>No recommendation generated yet.</p>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                    Run the autonomous AI calls to collect quotes and generate the best deal recommendation.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 11: HISTORY */}
          {activeTab === "history" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon indigo">
                    <History size={18} />
                  </div>
                  <div>
                    <h3>Negotiation History</h3>
                    <small>Past purchasing requests and recorded outcomes</small>
                  </div>
                </div>
              </div>

              {allNegotiations.length === 0 ? (
                <p style={{ textAlign: "center", color: "#94a3b8", padding: "30px" }}>
                  No past sessions found.
                </p>
              ) : (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Quantity</th>
                        <th>Budget</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allNegotiations.map((n) => (
                        <tr key={n.id}>
                          <td>
                            <b>{n.product}</b>
                          </td>
                          <td>{n.quantity} units</td>
                          <td>₹{fmt(n.budget)}</td>
                          <td>
                            <span className={`badge-state state-${n.status}`}>{n.status}</span>
                          </td>
                          <td>
                            <small>{n.created_at?.slice(0, 10)}</small>
                          </td>
                          <td>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "4px 10px", fontSize: "11px" }}
                              onClick={() => {
                                loadNegotiationDetails(n.id);
                                setActiveTab("dashboard");
                              }}
                            >
                              Load Session
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 12: SETTINGS & INTEGRATIONS */}
          {activeTab === "settings" && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon amber">
                    <Settings size={18} />
                  </div>
                  <div>
                    <h3>System Architecture & Telephony Diagnostics</h3>
                    <small>Live configuration status of backend subsystems</small>
                  </div>
                </div>
              </div>

              <div className="grid-2">
                {/* Telephony Status & Credentials Configuration */}
                <div style={{ background: "var(--bg-input)", padding: "20px", borderRadius: "var(--radius-md)" }}>
                  <h4 style={{ color: "white", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <PhoneCall size={16} color="#6366f1" /> Live Real Phone Calling (Twilio Telephony)
                  </h4>
                  <p style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: "1.6", marginBottom: "16px" }}>
                    <b>Current Status:</b>{" "}
                    {systemStatus?.twilio_configured ? (
                      <span style={{ color: "var(--success)", fontWeight: 700 }}>
                        ✓ Ready for Live Outbound Calls to Real Phones
                      </span>
                    ) : (
                      <span style={{ color: "var(--warning)", fontWeight: 600 }}>
                        ⚠ Free Simulated Demo Mode Active (No Twilio keys set)
                      </span>
                    )}
                    <br />
                    <b>Sender Number:</b> {systemStatus?.twilio_phone_number || "Not Configured"} <br />
                    <b>Webhook Base:</b> {systemStatus?.webhook_base_url || "Localhost"}
                  </p>

                  {/* Telephony Config Form */}
                  <form onSubmit={handleSaveTelephony}>
                    <div className="form-group" style={{ marginBottom: "10px" }}>
                      <label style={{ fontSize: "11px" }}>Twilio Account SID</label>
                      <input
                        className="form-control"
                        style={{ fontSize: "12px" }}
                        value={twilioSettings.twilio_account_sid}
                        onChange={(e) =>
                          setTwilioSettings({ ...twilioSettings, twilio_account_sid: e.target.value })
                        }
                        placeholder="e.g. ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      />
                    </div>

                    <div className="form-group" style={{ marginBottom: "10px" }}>
                      <label style={{ fontSize: "11px" }}>Twilio Auth Token</label>
                      <input
                        type="password"
                        className="form-control"
                        style={{ fontSize: "12px" }}
                        value={twilioSettings.twilio_auth_token}
                        onChange={(e) =>
                          setTwilioSettings({ ...twilioSettings, twilio_auth_token: e.target.value })
                        }
                        placeholder="Enter Twilio Auth Token"
                      />
                    </div>

                    <div className="grid-2" style={{ gap: "10px", marginBottom: "10px" }}>
                      <div className="form-group">
                        <label style={{ fontSize: "11px" }}>Twilio Phone Number</label>
                        <input
                          className="form-control"
                          style={{ fontSize: "12px" }}
                          value={twilioSettings.twilio_phone_number}
                          onChange={(e) =>
                            setTwilioSettings({ ...twilioSettings, twilio_phone_number: e.target.value })
                          }
                          placeholder="+1xxxxxxxxxx"
                        />
                      </div>
                      <div className="form-group">
                        <label style={{ fontSize: "11px" }}>Public Webhook URL (ngrok)</label>
                        <input
                          className="form-control"
                          style={{ fontSize: "12px" }}
                          value={twilioSettings.webhook_base_url}
                          onChange={(e) =>
                            setTwilioSettings({ ...twilioSettings, webhook_base_url: e.target.value })
                          }
                          placeholder="https://xxxx.ngrok-free.app"
                        />
                      </div>
                    </div>

                    <small style={{ display: "block", color: "#94a3b8", fontSize: "11px", marginBottom: "12px", lineHeight: "1.4" }}>
                      💡 For real calls to physical phones, Twilio dials the number and calls your <code>WEBHOOK_BASE_URL</code> to speak and gather supplier quotes. Use an ngrok HTTPS tunnel if testing locally.
                    </small>

                    <button className="btn btn-primary" type="submit" disabled={busy} style={{ width: "100%", justifyContent: "center" }}>
                      {busy ? <Loader2 className="spin" size={14} /> : <ShieldCheck size={14} />}
                      <span>Save & Verify Telephony Credentials</span>
                    </button>
                  </form>

                  {/* Test Call Trigger */}
                  <div
                    style={{
                      marginTop: "18px",
                      paddingTop: "14px",
                      borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                    }}
                  >
                    <label style={{ fontSize: "12px", color: "white", fontWeight: 600, display: "block", marginBottom: "8px" }}>
                      📞 Test Outbound Dial to My Phone
                    </label>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <input
                        className="form-control"
                        style={{ fontSize: "12px", flex: 1 }}
                        value={testCallPhone}
                        onChange={(e) => setTestCallPhone(e.target.value)}
                        placeholder="Your Mobile (e.g. 9845012345)"
                      />
                      <button
                        className="btn btn-secondary"
                        onClick={handleTestCall}
                        disabled={busy || !testCallPhone.trim()}
                        style={{ whiteSpace: "nowrap", fontSize: "12px" }}
                      >
                        {busy ? <Loader2 className="spin" size={12} /> : <PhoneCall size={12} />}
                        <span>Ring My Phone</span>
                      </button>
                    </div>
                  </div>

                  {telephonyStatusMsg && (
                    <div
                      style={{
                        marginTop: "12px",
                        padding: "8px 12px",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "12px",
                        background:
                          telephonyStatusMsg.type === "success"
                            ? "var(--success-bg)"
                            : "var(--danger-bg)",
                        color:
                          telephonyStatusMsg.type === "success"
                            ? "var(--success)"
                            : "var(--danger)",
                        border: `1px solid ${
                          telephonyStatusMsg.type === "success"
                            ? "var(--success-border)"
                            : "var(--danger-border)"
                        }`,
                      }}
                    >
                      {telephonyStatusMsg.text}
                    </div>
                  )}
                </div>

                {/* AI & Language Engines */}
                <div style={{ background: "var(--bg-input)", padding: "20px", borderRadius: "var(--radius-md)" }}>
                  <h4 style={{ color: "white", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Bot size={16} color="#c084fc" /> AI & Language Engines
                  </h4>
                  <p style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: "1.6" }}>
                    <b>NLP Engine:</b> {systemStatus?.ai_provider || "Rule-based Built-in NLP (Active)"} <br />
                    <b>Database Storage:</b> {systemStatus?.database_type || "SQLite (Local File Persistence)"} <br />
                    <b>Human Approval Constraint:</b> Strict Code Enforcement (Mandatory sign-off before order confirmation)
                  </p>

                  <div style={{ marginTop: "16px" }}>
                    <small style={{ color: "#94a3b8", fontWeight: 600 }}>Supported Dialect & Voice Recognition:</small>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                      {systemStatus?.supported_languages?.map((l) => (
                        <span
                          key={l}
                          style={{
                            fontSize: "11px",
                            padding: "4px 10px",
                            borderRadius: "12px",
                            background: "var(--bg-card)",
                            color: "#c7d2fe",
                            border: "1px solid var(--border-color)",
                          }}
                        >
                          {l}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginTop: "20px", padding: "14px", background: "rgba(99, 102, 241, 0.08)", borderRadius: "var(--radius-sm)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                    <h5 style={{ color: "#a5b4fc", margin: "0 0 6px 0", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Sparkles size={14} /> How DealPilot AI Works End-to-End
                    </h5>
                    <ol style={{ fontSize: "11px", color: "#cbd5e1", lineHeight: "1.6", margin: 0, paddingLeft: "16px" }}>
                      <li>When a supplier is added or called, DealPilot dials their phone number.</li>
                      <li>It speaks to the representative in their preferred regional language.</li>
                      <li>It enquires about product specifications, unit pricing, GST, warranty, and delivery.</li>
                      <li>If the initial quote is above budget, DealPilot counters with your target price.</li>
                      <li>It extracts the final quotation into structured data and logs the evidence.</li>
                      <li>The scoring engine deterministically compares all offers and ranks the Best Business Deal!</li>
                    </ol>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* MODAL 1: CALL CONFIRMATION */}
      {showCallConfirmModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ color: "white", display: "flex", alignItems: "center", gap: "8px" }}>
                <PhoneCall size={18} color="#6366f1" /> Confirm Autonomous AI Calls
              </h3>
              <button
                style={{ background: "transparent", border: "none", color: "white", cursor: "pointer" }}
                onClick={() => setShowCallConfirmModal(false)}
              >
                ×
              </button>
            </div>

            <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: "1.6" }}>
              You are about to start autonomous calling to <b>{suppliers.length} supplier(s)</b>.
            </p>

            <div
              style={{
                background: "var(--bg-input)",
                padding: "14px",
                borderRadius: "var(--radius-sm)",
                margin: "14px 0",
                fontSize: "12px",
                lineHeight: "1.6",
              }}
            >
              <b>Calling Mode:</b> {callingMode.toUpperCase()}{" "}
              {callingMode === "simulated"
                ? "— (Offline Software Simulation)"
                : "— (Real Telecom Outbound Calling via Twilio)"}
              <br />
              <b>Authorized Budget:</b> ₹{fmt(negotiation?.budget)}
              <br />
              <b>Estimated Rounds:</b> Up to {negotiation?.max_negotiation_rounds || 3} turns per supplier.
              <br />
              <b>Human Supervisor:</b> You will review and approve the final deal before any purchase.
            </div>

            {callingMode === "simulated" && (
              <div
                style={{
                  background: "rgba(245, 158, 11, 0.12)",
                  border: "1px solid var(--warning-border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "10px 14px",
                  marginBottom: "14px",
                  color: "#fbbf24",
                  fontSize: "11px",
                  lineHeight: "1.5",
                }}
              >
                <b>Note on Simulated Demo Mode:</b> In this mode, DealPilot AI conducts an internal software
                simulation so you can test multilingual negotiations without a paid carrier account.
                <u>Your physical mobile phone will not ring</u>. To make your actual phone ring, configure Twilio
                credentials in <code>backend/.env</code> and switch to <b>Real Phone Calls</b>.
              </div>
            )}

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCallConfirmModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleStartCalls} disabled={busy}>
                {busy ? <Loader2 className="spin" size={15} /> : <Play size={15} />}
                <span>Authorize & Start Calls</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: HUMAN APPROVAL / REJECTION */}
      {showApprovalModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ color: "white", display: "flex", alignItems: "center", gap: "8px" }}>
                {approvalType === "approve" ? (
                  <ThumbsUp size={18} color="var(--success)" />
                ) : (
                  <ThumbsDown size={18} color="var(--danger)" />
                )}
                <span>
                  {approvalType === "approve" ? "Approve Recommendation" : "Reject Recommendation"}
                </span>
              </h3>
              <button
                style={{ background: "transparent", border: "none", color: "white", cursor: "pointer" }}
                onClick={() => setShowApprovalModal(false)}
              >
                ×
              </button>
            </div>

            <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: "1.6" }}>
              Supplier: <b>{recommendation?.recommended_supplier}</b> <br />
              Final Quoted Price: <b>₹{fmt(recommendation?.final_price)}</b>
            </p>

            <div className="form-group" style={{ marginTop: "14px" }}>
              <label>Supervisor Authorization Notes</label>
              <textarea
                className="form-control"
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="e.g. Terms reviewed and delivery timeline verified with warehouse..."
              />
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowApprovalModal(false)}>
                Cancel
              </button>
              <button
                className={`btn ${approvalType === "approve" ? "btn-success" : "btn-danger"}`}
                onClick={handleApprovalSubmit}
                disabled={busy}
              >
                {approvalType === "approve" ? "Confirm Approval" : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
