import fs from 'node:fs'

const path = 'src/main.tsx'
let main = fs.readFileSync(path, 'utf8')

if (!main.includes('client-score-panel')) {
  main = main.replace(
    "const [checking,setChecking]=useState<string|null>(null),[removing,setRemoving]=useState<Client|null>(null),[saving,setSaving]=useState(false),[msg,setMsg]=useState(''),[error,setError]=useState('');",
    "const [checking,setChecking]=useState<string|null>(null),[removing,setRemoving]=useState<Client|null>(null),[saving,setSaving]=useState(false),[simulating,setSimulating]=useState<string|null>(null),[msg,setMsg]=useState(''),[error,setError]=useState('');"
  )
  const marker = "const remove=async()=>{if(!removing)return;"
  const simulation = "const simulateIncident=async(id:string)=>{setSimulating(id);setMsg('');setError('');try{const r=await api<any>('/api/v1/clients/'+id+'/simulate-incident',{method:'POST'},token);await onChanged();const incidentId=r.incident_ids?.[0];if(incidentId)onIncident(incidentId);else setMsg('Client incident created.')}catch(x){setError((x as Error).message)}finally{setSimulating(null)}};\n "
  if (main.includes(marker) && !main.includes('const simulateIncident=')) main = main.replace(marker, simulation + marker)

  const statusMarker = '<div className="inventory-status"><span className={c.status===\'DOWN\'?\'online-badge down-text\':\'online-badge\'}><i/> {c.status}</span><strong>{c.last_response_ms ? c.last_response_ms+\' ms\' : \'—\'}</strong></div>'
  const scorePanel = statusMarker + '<div className="client-score-panel"><div><span>CLIENT PERFORMANCE</span><strong>{(c as any).score??0}/85</strong></div><div className="score-track"><i style={{width:Math.min(100,Math.round((((c as any).score??0)/85)*100))+\'%\'}}/></div><small>Logs {(c as any).performance?.components?.logs?.events??0} · Deployments {(c as any).performance?.components?.deployments?.events??0} · Audits {(c as any).performance?.components?.audits?.events??0} · Tokens {(c as any).performance?.components?.tokens?.estimated??0}</small></div>'
  if (main.includes(statusMarker)) main = main.replace(statusMarker, scorePanel)

  const removeButton = '<button className="danger small" onClick={()=>setRemoving(c)}>Remove Client</button>'
  const simulateButton = '<button className="ghost small" disabled={simulating===c.client_id} onClick={()=>simulateIncident(c.client_id)}>{simulating===c.client_id?\'Creating incident…\':\'Simulate client incident\'}</button>' + removeButton
  if (main.includes(removeButton) && !main.includes('Simulate client incident')) main = main.replace(removeButton, simulateButton)

  fs.writeFileSync(path, main)
}

const cssPath = 'src/style.css'
let css = fs.readFileSync(cssPath, 'utf8')
if (!css.includes('.client-score-panel')) {
  css += `\n.client-score-panel{grid-column:1/-1;border:1px solid var(--border);border-radius:14px;padding:12px 14px;background:var(--card)}.client-score-panel>div:first-child{display:flex;justify-content:space-between;align-items:center}.client-score-panel span{font-size:10px;letter-spacing:.12em;color:var(--muted);font-weight:800}.client-score-panel strong{font-size:20px}.score-track{height:6px;border-radius:999px;background:var(--border);overflow:hidden;margin:9px 0}.score-track i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#06b6d4,#14b8a6)}.client-score-panel small{color:var(--muted);font-size:10px}\n`
  fs.writeFileSync(cssPath, css)
}
