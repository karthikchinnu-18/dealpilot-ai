import { useEffect, useState } from "react";
import { Activity, ArrowRight, BadgeCheck, Bot, Building2, CheckCircle2, CircleAlert, Clock3, FileText, Headphones, LoaderCircle, PhoneCall, Plus, Radio, Scale, ShieldCheck, Sparkles, Wallet } from "lucide-react";

const API = "http://127.0.0.1:8000";
const emptyOffer = () => ({business_name:"",total_price:"",delivery_days:"3",terms:"",evidence_note:"",evidence_status:"unverified",source_type:"other"});

export default function App() {
  const [apiState,setApiState] = useState("checking");
  const [product,setProduct] = useState("Printed T-shirts");
  const [quantity,setQuantity] = useState("100");
  const [budget,setBudget] = useState("12000");
  const [deadline,setDeadline] = useState("Within 5 days");
  const [priority,setPriority] = useState("best_value");
  const [negotiation,setNegotiation] = useState(null);
  const [offers,setOffers] = useState([]);
  const [recommendation,setRecommendation] = useState(null);
  const [offer,setOffer] = useState(emptyOffer());
  const [phoneNumber,setPhoneNumber] = useState("");
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState("");

  async function checkHealth() {
    try { const r=await fetch(`${API}/health`); if(!r.ok) throw new Error(); setApiState("online"); }
    catch { setApiState("offline"); }
  }
  useEffect(()=>{checkHealth();},[]);

  async function createRequest(e) {
    e.preventDefault(); setBusy(true); setMessage("");
    try {
      const r=await fetch(`${API}/api/negotiations`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({product,quantity:Number(quantity),budget:Number(budget),deadline,priorities:[priority]})});
      const d=await r.json(); if(!r.ok) throw new Error(JSON.stringify(d.detail||"Could not create request"));
      setNegotiation(d);setOffers([]);setRecommendation(null);setMessage("Request created. No businesses have been contacted.");
    } catch(err){setMessage(`Error: ${err.message}. Check the backend terminal.`);}
    finally{setBusy(false);}
  }

  async function refreshRecommendation(id, nextOffers) {
    const r=await fetch(`${API}/api/negotiations/${id}/recommendation`);
    const d=await r.json();setRecommendation(d);setOffers(nextOffers);
  }

  async function addOffer(e) {
    e.preventDefault(); if(!negotiation)return;setBusy(true);setMessage("");
    try {
      const payload={...offer,total_price:Number(offer.total_price),delivery_days:Number(offer.delivery_days)};
      const r=await fetch(`${API}/api/negotiations/${negotiation.id}/offers`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const d=await r.json();if(!r.ok)throw new Error(JSON.stringify(d.detail||"Could not add offer"));
      const next=[...offers,d];setOffer(emptyOffer());await refreshRecommendation(negotiation.id,next);setMessage("Offer added. Check its evidence status before relying on the recommendation.");
    }catch(err){setMessage(`Error: ${err.message}`);}finally{setBusy(false);}
  }

  function callSupplier() {
    const normalized = phoneNumber.trim().replace(/[^0-9+]/g, "");
    if (!normalized || normalized.replace(/\\D/g, "").length < 7) {
      setMessage("Enter a valid supplier phone number first. This opens your device dialer; you must place the call yourself.");
      return;
    }
    setMessage("Opening your device dialer. Confirm the number and place the call yourself. DealPilot AI does not record or automate this call.");
    window.location.href = `tel:${normalized}`;
  }

  function loadDemo() {
    setProduct("Printed T-shirts");setQuantity("100");setBudget("12000");setDeadline("Within 5 days");setPriority("best_value");
    setOffer({business_name:"Demo Print House A",total_price:"12000",delivery_days:"3",terms:"Printing included; sample terms only",evidence_note:"Fictional sample offer for UI testing",evidence_status:"demo",source_type:"demo"});
    setMessage("Demo form loaded. This fictional sample is not a real quote.");
  }

  const best=recommendation?.recommendation;
  const fmt=n=>Number(n).toLocaleString("en-IN",{maximumFractionDigits:2});

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="logo"><Scale size={22}/></div><div><b>DealPilot <span>AI</span></b><small>THE NEGOTIATOR</small></div></div>
      <p className="side-label">WORKSPACE</p>
      <div className="nav active"><Activity size={17}/> Negotiation desk</div>
      <div className="side-bottom"><div className="connection"><i className={apiState==="online"?"online":""}/><span>Backend {apiState==="online"?"connected":apiState==="checking"?"checking":"offline"}</span></div><div className="side-note"><ShieldCheck size={16}/> Transparent offers. Evidence-first decisions. Human approval before commitments.</div></div>
    </aside>
    <main className="main">
      <header className="topbar"><span>Workspaceã€€â€ºã€€<b>Negotiation desk</b></span><span className="pill"><i/> HACKATHON PROTOTYPE</span></header>
      <section className="hero">
        <div><div className="eyebrow"><Sparkles size={14}/> CHALLENGE 02 Â· VOICE AI AGENT</div><h1>Better deals.<br/><em>Backed by evidence.</em></h1><p>Define what you need, collect business offers, and compare the trade-offs in one place.</p><div className="hero-tags"><span><PhoneCall size={14}/> Voice workflow integration pending</span><span><BadgeCheck size={14}/> Evidence-first decisions</span></div></div>
        <div className="voice-visual"><div className="orb"><Bot size={40}/></div><div className="wave">{Array.from({length:25},(_,i)=><i key={i} style={{height:`${10+Math.abs(Math.sin(i*1.6))*42}px`}}/>)}</div><small>VOICE AGENTã€€<b>NOT CONNECTED</b></small></div>
      </section>
      <div className="notice"><CircleAlert size={17}/><div><b>Prototype status:</b> Call Supplier opens your device dialer for a human-placed call; automated AI calling is not connected. Add actual quotes or clearly labelled demo offers; never present sample data as a real call or quote.</div></div>

      <div className="section-head"><div><small>STEP 01</small><h2>Define your negotiation</h2><p>Tell DealPilot what matters most to compare offers.</p></div><button className="secondary" onClick={loadDemo}><Sparkles size={15}/> Load sample form</button></div>
      <div className="grid">
        <form className="panel" onSubmit={createRequest}>
          <div className="panel-title"><div className="icon purple"><Building2 size={18}/></div><div><h3>Purchase requirements</h3><p>Start with a clear, measurable request.</p></div></div>
          <label>Product or service<input value={product} onChange={e=>setProduct(e.target.value)} required minLength="2" maxLength="150"/></label>
          <div className="two"><label>Quantity<input type="number" min="1" max="100000" value={quantity} onChange={e=>setQuantity(e.target.value)} required/></label><label>Budget (â‚¹)<input type="number" min="1" step=".01" value={budget} onChange={e=>setBudget(e.target.value)} required/></label></div>
          <label>Required by<input value={deadline} onChange={e=>setDeadline(e.target.value)} required maxLength="100"/></label>
          <label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)}><option value="best_value">Best overall value</option><option value="lowest_price">Lowest price</option><option value="fastest_delivery">Fastest delivery</option></select></label>
          <button className="primary" disabled={busy||apiState!=="online"}>{busy?<LoaderCircle className="spin" size={17}/>:<Radio size={17}/>} Create negotiation request <ArrowRight size={16}/></button>
          <p className="hint">Creating a request does not call a business or commit to a purchase.</p>
        </form>
        <section className="panel">
          <div className="panel-title"><div className="icon orange"><Headphones size={18}/></div><div><h3>Agent workflow</h3><p>From request to evidence-backed decision.</p></div></div>
          {[
            ["1","Understand request","Requirements and priorities","READY"],
            ["2","Contact businesses","Outbound voice integration","PENDING"],
            ["3","Verify offers","Price, terms, and source","MANUAL"],
            ["4","Compare & recommend","Transparent scoring","READY AFTER OFFERS"]
          ].map((s,i)=><div className="workflow" key={s[0]}><div className="workflow-icon">{i===0?<CheckCircle2 size={17}/>:i===1?<PhoneCall size={17}/>:i===2?<FileText size={17}/>:<Scale size={17}/>}</div><div className="workflow-copy"><b>{s[1]}</b><small>{s[2]}</small></div><span className="state">{s[3]}</span></div>)}
          <div className="safe-note"><ShieldCheck size={16}/> Human approval required before any purchase or binding commitment.</div>
        </section>
      </div>
      {message&&<div className={`message ${message.startsWith("Error")?"error":"success"}`}>{message}</div>}

      {negotiation&&<section className="offers-section">
        <div className="section-head"><div><small>STEP 02</small><h2>Capture and compare offers</h2><p>Enter a real quote, or mark it as demo data for testing.</p></div><span className="id">ID {negotiation.id.slice(0,8).toUpperCase()}</span></div>
        <div className="grid">
          <form className="panel" onSubmit={addOffer}>
            <div className="panel-title"><div className="icon green"><Plus size={18}/></div><div><h3>Offer details</h3><p>Keep source and verification status explicit.</p></div></div>
            <label>Business name<input value={offer.business_name} onChange={e=>setOffer({...offer,business_name:e.target.value})} required minLength="2" maxLength="120"/></label>
            <label>Supplier phone number (optional)<input type="tel" inputMode="tel" value={phoneNumber} onChange={e=>setPhoneNumber(e.target.value)} placeholder="e.g. +91 98765 43210" maxLength="25"/></label>
            <button className="secondary" type="button" onClick={callSupplier}><PhoneCall size={16}/> Call supplier on this device</button>
            <p className="hint">Opens your device's phone app/dialer. You place the call manually; calls are not recorded or automated by DealPilot AI.</p>
            <div className="two"><label>Total price (â‚¹)<input type="number" min=".01" step=".01" value={offer.total_price} onChange={e=>setOffer({...offer,total_price:e.target.value})} required/></label><label>Delivery (days)<input type="number" min="0" max="3650" value={offer.delivery_days} onChange={e=>setOffer({...offer,delivery_days:e.target.value})} required/></label></div>
            <label>Terms / conditions<textarea value={offer.terms} onChange={e=>setOffer({...offer,terms:e.target.value})} maxLength="1000" placeholder="Taxes, shipping, discount conditionsâ€¦"/></label>
            <label>Evidence note<input value={offer.evidence_note} onChange={e=>setOffer({...offer,evidence_note:e.target.value})} required minLength="3" maxLength="1000" placeholder="e.g. Quote email received today"/></label>
            <div className="two"><label>Evidence status<select value={offer.evidence_status} onChange={e=>setOffer({...offer,evidence_status:e.target.value})}><option value="unverified">Unverified</option><option value="verified">Verified</option><option value="demo">Demo / fictional</option></select></label><label>Source<select value={offer.source_type} onChange={e=>setOffer({...offer,source_type:e.target.value})}><option value="other">Other</option><option value="phone">Phone</option><option value="email">Email</option><option value="website">Website</option><option value="demo">Demo</option></select></label></div>
            <button className="primary" disabled={busy||apiState!=="online"}><Plus size={17}/> Add offer & compare</button>
          </form>
          <div className="panel">
            <div className="panel-title"><div className="icon blue"><Scale size={18}/></div><div><h3>Offer comparison</h3><p>{offers.length} offer{offers.length===1?"":"s"} captured</p></div></div>
            {!offers.length?<div className="empty"><Wallet size={28}/><b>No offers yet</b><p>Add real quotes, or use clearly marked demo data to test the workflow.</p></div>:offers.map(o=><div className="offer" key={o.id}><div className="offer-top"><b>{o.business_name}</b><span className={`badge ${o.evidence_status}`}>{o.evidence_status}</span></div><strong>â‚¹{fmt(o.total_price)}</strong><p>{o.delivery_days} day(s) Â· {o.source_type}</p><small>{o.evidence_note}</small></div>)}
            {best&&<div className="recommendation"><div className="rec-label"><Sparkles size={15}/> CURRENT RECOMMENDATION</div><h3>{best.business_name}</h3><strong>â‚¹{fmt(best.total_price)}</strong><p>Score: {recommendation.score}/100 Â· Evidence: {best.evidence_status}</p><ul>{recommendation.reasons?.map((r,i)=><li key={i}>{r}</li>)}</ul><small>{recommendation.note}</small></div>}
          </div>
        </div>
      </section>}
      <footer><b>DealPilot AI</b><span>Hackathon starter Â· Transparent by design</span><span>Real calling integration not yet connected</span></footer>
    </main>
  </div>;
}

