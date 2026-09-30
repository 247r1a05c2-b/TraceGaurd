import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL || 'engineer@tracegaurd.ai';
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || 'TraceGaurd@123';

async function jsonRequest(path, options = {}, token) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  });
  let data = {};
  try { data = await response.json(); } catch {}
  if (!response.ok) throw new Error(data.detail || data.message || 'Request failed');
  return data;
}

function normalizeAnalysis(data) {
  return {
    ...data,
    diagnosisSteps: data.diagnosis_steps || data.steps || [],
    repairSteps: data.repair_steps || data.repair_plan || [],
    actions: data.actions || [],
    ragContext: data.rag_context || [],
    agentTrace: data.agent_trace || [],
    timeline: data.timeline || [],
    evidence: data.evidence || []
  };
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('tracegaurd_token'));
  const [email, setEmail] = useState(localStorage.getItem('tracegaurd_email') || DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [incidents, setIncidents] = useState([]);
  const [clients, setClients] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selected, setSelected] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loginError, setLoginError] = useState('');
  const [approval, setApproval] = useState(null);
  const [activeView, setActiveView] = useState('Command Center');

  const logout = () => {
    localStorage.removeItem('tracegaurd_token');
    localStorage.removeItem('tracegaurd_email');
    setToken(null);
    setAnalysis(null);
  };

  const load = async () => {
    try {
      const [incidentData, clientData, metricData] = await Promise.all([
        jsonRequest('/api/v1/incidents', {}, token),
        jsonRequest('/api/v1/clients', {}, token),
        jsonRequest('/api/v1/metrics', {}, token)
      ]);
      setIncidents(incidentData);
      setClients(clientData);
      setMetrics(metricData);
      setError('');
    } catch (err) {
      if (String(err.message).toLowerCase().includes('session') || String(err.message).toLowerCase().includes('engineer')) logout();
      setError(err.message);
    }
  };

  useEffect(() => { if (token) load(); }, [token]);

  const login = async (event) => {
    event.preventDefault();
    setLoginError('');
    try {
      const result = await jsonRequest('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      localStorage.setItem('tracegaurd_token', result.access_token);
      localStorage.setItem('tracegaurd_email', result.engineer || email);
      setToken(result.access_token);
      setEmail(result.engineer || email);
    } catch (err) {
      setLoginError(err.message);
    }
  };

  const simulate = async () => {
    setLoading(true);
    try {
      await jsonRequest('/api/v1/simulate/checkout', { method: 'POST' }, token);
      await load();
      setError('');
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const analyze = async (incidentId) => {
    setSelected(incidentId);
    setLoading(true);
    setApproval(null);
    try {
      const result = await jsonRequest(`/api/v1/incidents/${incidentId}/analysis`, {}, token);
      setAnalysis(normalizeAnalysis(result));
      setError('');
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const approve = async (action, approved) => {
    if (!selected) return;
    setLoading(true);
    try {
      const result = await jsonRequest(`/api/v1/incidents/${selected}/approve`, {
        method: 'POST',
        body: JSON.stringify({ action, approved })
      }, token);
      setApproval(result);
      if (approved && result.approval_id) {
        const execution = await jsonRequest(`/api/v1/incidents/${selected}/execute`, {
          method: 'POST',
          body: JSON.stringify({ action, approval_id: result.approval_id })
        }, token);
        setApproval({ ...result, execution });
      }
      await load();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const approvalCount = useMemo(() => analysis?.actions?.filter(a => a.risk === 'APPROVAL').length || 0, [analysis]);

  if (!token) {
    return (
      <div className="login">
        <div className="login-card">
          <div className="brand">TRACE<span>GAURD</span></div>
          <div className="tag">MULTI-AGENT AI INCIDENT COMMANDER</div>
          <h1>Software Engineer Login</h1>
          <p>Securely monitor clients, investigate incidents, review AI diagnosis and approve controlled remediation.</p>
          <form onSubmit={login}>
            <label>Email<input value={email} onChange={e => setEmail(e.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
            {loginError && <div className="error">{loginError}</div>}
            <button type="submit">Sign in to Command Center</button>
          </form>
          <small>Demo: {DEMO_EMAIL} / {DEMO_PASSWORD}</small>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <aside>
        <div className="brand">TRACE<span>GAURD</span></div>
        <div className="tag">MULTI-AGENT AI INCIDENT COMMANDER</div>
        <nav>
          {['Command Center', 'Clients', 'Incidents', 'Agent Trace', 'RAG Evidence', 'Audit Timeline'].map(item => (
            <a key={item} className={activeView === item ? 'active' : ''} onClick={() => setActiveView(item)}>{item}</a>
          ))}
        </nav>
        <div className="sidebottom">
          <div><span className="dot"></span>System operational</div>
          <small>{email}</small>
          <button className="logout" onClick={logout}>Sign out</button>
        </div>
      </aside>

      <main>
        <header>
          <div>
            <p className="eyebrow">LANGGRAPH · LLM · RAG · GUARDRAILS · HUMAN APPROVAL</p>
            <h1>Incident Command Center</h1>
            <p className="muted">Monitor clients → detect incidents → diagnose root cause → review repair plan → approve → verify</p>
          </div>
          <button onClick={simulate} disabled={loading}>{loading ? 'PROCESSING...' : '＋ Simulate Client Incident'}</button>
        </header>

        {error && <div className="error">{error}</div>}

        <section className="metrics">
          <div><small>ACTIVE INCIDENTS</small><strong>{metrics?.active_incidents ?? incidents.length}</strong></div>
          <div><small>CLIENTS MONITORED</small><strong>{metrics?.clients_monitored ?? clients.length}</strong></div>
          <div><small>ROOT-CAUSE CONFIDENCE</small><strong>{analysis ? `${analysis.confidence}%` : '—'}</strong></div>
          <div><small>APPROVAL ACTIONS</small><strong>{analysis ? approvalCount : '—'}</strong></div>
        </section>

        <section className="panel clientbar">
          <div className="panelhead"><h2>Client Monitoring</h2><span>LIVE SERVICE INVENTORY</span></div>
          <div className="clients">
            {clients.map(client => (
              <div className="client" key={client.client_id}>
                <span className="online"></span>
                <div><b>{client.name}</b><small>{client.service} · {client.environment}</small></div>
                <strong>{client.incidents} incidents</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="grid">
          <div className="panel">
            <div className="panelhead"><h2>Incident Queue</h2><span>{incidents.length} detected</span></div>
            {incidents.length === 0 ? (
              <div className="empty">No incidents yet. Use <b>Simulate Client Incident</b> to demonstrate the complete diagnosis and repair workflow.</div>
            ) : incidents.map(incident => (
              <div key={incident.incident_id} className={`incident ${selected === incident.incident_id ? 'selected' : ''}`} onClick={() => analyze(incident.incident_id)}>
                <div><b>{incident.incident_id}</b><p>{incident.title}</p></div>
                <div><span className="critical">{incident.severity}</span><small>{incident.event_count} events</small></div>
              </div>
            ))}
          </div>

          <div className="panel analysis">
            <div className="panelhead"><h2>AI Investigation</h2><span>{analysis ? (analysis.llm_used ? 'LLM + RAG' : 'LANGGRAPH + RAG FALLBACK') : 'WAITING'}</span></div>
            {!analysis ? (
              <div className="empty">Select an incident. TraceGaurd executes Ingestion → Noise Filter → Correlation → RAG → Root Cause → Diagnostics → Guardrail → Timeline.</div>
            ) : (
              <>
                <div className="cause">
                  <small>LEADING ROOT-CAUSE HYPOTHESIS</small>
                  <h3>{analysis.root_cause}</h3>
                  <p>{analysis.summary}</p>
                  <div className="confidence"><span>Evidence confidence</span><b>{analysis.confidence}%</b></div>
                  <p className="disclaimer">Confidence represents evidence support for the hypothesis; it is not a guarantee of correctness.</p>
                </div>

                <div className="workflow-strip">
                  {['Ingestion', 'Noise Filter', 'Correlation', 'RAG', 'Root Cause', 'Diagnostic', 'Guardrail', 'Timeline'].map((agent, index) => (
                    <div key={agent} className="workflow-node"><span>{String(index + 1).padStart(2, '0')}</span>{agent}</div>
                  ))}
                </div>
              </>
            )}
          </div>
        </section>

        {analysis && (
          <>
            <section className="panel">
              <div className="panelhead"><h2>Diagnosis Steps</h2><span>{analysis.diagnosisSteps.length} STEPS GENERATED</span></div>
              <div className="steps">
                {analysis.diagnosisSteps.map((step, index) => (
                  <div className="step" key={index}>
                    <div className="num">{index + 1}</div>
                    <div><b>{step.stage || `Diagnostic step ${index + 1}`}</b><p>{step.finding || step.description || step.step}</p><small>Evidence: {(step.evidence || []).join(' · ') || 'Derived from incident context'}</small></div>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel repair-panel">
              <div className="panelhead"><h2>Repair Plan</h2><span>HUMAN-GATED</span></div>
              {analysis.repairSteps.length ? analysis.repairSteps.map((step, index) => (
                <div className="repair-step" key={index}><div className="repair-icon">✓</div><div><b>{step.stage || step.title || `Repair step ${index + 1}`}</b><p>{step.finding || step.description || step.step || step.validation}</p></div></div>
              )) : <div className="empty">The Diagnostic Agent generated candidate remediation actions below. Production mutations remain blocked until an engineer approves them.</div>}
            </section>

            <section className="panel actions">
              <div className="panelhead"><h2>Guardrail & Human Approval</h2><span>{analysis.approval_state || (approvalCount ? 'PENDING_HUMAN_REVIEW' : 'SAFE')}</span></div>
              {analysis.actions.map((action, index) => (
                <div className="action" key={index}>
                  <div><b>{action.action}</b><p>{action.reason}</p></div>
                  <strong className={action.risk === 'SAFE' ? 'safe' : action.risk === 'APPROVAL' ? 'approval' : 'blocked'}>{action.risk}</strong>
                  {action.risk === 'APPROVAL' && <div className="actionbuttons"><button disabled={loading} onClick={() => approve(action.action, true)}>Approve & Execute</button><button disabled={loading} className="secondary" onClick={() => approve(action.action, false)}>Reject</button></div>}
                </div>
              ))}
              {approval && (
                <div className="approvalbox">
                  <b>{approval.state}</b> · {approval.action}
                  {approval.execution && <p>{approval.execution.message || 'Approved remediation executed.'}</p>}
                </div>
              )}
            </section>

            <section className="panel">
              <div className="panelhead"><h2>Verification</h2><span>POST-REMEDIATION SAFETY CHECK</span></div>
              {approval?.execution?.verification ? approval.execution.verification.map((item, index) => <div className="verification" key={index}><span>✓</span><p>{typeof item === 'string' ? item : item.message || JSON.stringify(item)}</p></div>) : <div className="empty">After an approved remediation, TraceGaurd records verification evidence here.</div>}
            </section>

            <section className="panel">
              <div className="panelhead"><h2>Evaluation Metrics</h2><span>EVIDENCE-WEIGHTED</span></div>
              <div className="eval">
                <Metric label="Root-cause confidence" value={analysis.evaluation?.root_cause_confidence ?? analysis.confidence} />
                <Metric label="Evidence coverage" value={analysis.evaluation?.evidence_coverage ?? 0} />
                <Metric label="Workflow completeness" value={analysis.evaluation?.workflow_completeness ?? 0} />
                <Metric label="Diagnosis quality" value={analysis.evaluation?.diagnosis_quality ?? 0} />
              </div>
            </section>

            <section className="panel rag">
              <div className="panelhead"><h2>RAG Evidence</h2><span>GROUNDED RUNBOOK CONTEXT</span></div>
              {analysis.ragContext.map((doc, index) => <div className="ragitem" key={index}><div><b>{doc.id} · {doc.title}</b><p>{doc.content}</p></div><strong>{Math.round((doc.score || 0) * 100)}%</strong></div>)}
            </section>

            <section className="panel trace">
              <div className="panelhead"><h2>Agent Trace</h2><span>LANGGRAPH EXECUTION</span></div>
              {analysis.agentTrace.map((agent, index) => <div className="agent" key={index}><span className="check">✓</span><b>{agent.agent}</b><span>{agent.output}</span><em>{agent.status}</em></div>)}
            </section>

            <section className="panel timeline">
              <div className="panelhead"><h2>Evidence Timeline</h2><span>CHRONOLOGICAL</span></div>
              {analysis.timeline.map((event, index) => <div className="event" key={index}><time>{new Date(event.timestamp).toLocaleTimeString()}</time><span className={`badge ${event.severity}`}>{event.severity}</span><b>{event.service}</b><p>{event.message}</p></div>)}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function Metric({ label, value }) {
  const safe = Math.max(0, Math.min(100, Number(value) || 0));
  return <div className="metric"><div><span>{label}</span><b>{safe}%</b></div><div className="bar"><i style={{ width: `${safe}%` }} /></div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
