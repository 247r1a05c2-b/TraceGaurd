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

  main = main.replace(
    'clients.map(c=><article className="inventory-item" key={c.client_id}>',
    'clients.map(c=>{const performance=(c as any).performance||{};const score=Number((c as any).score??performance.score??0);return <article className="inventory-item" key={c.client_id}>'
  )
  main = main.replace(
    '</div><div className="inventory-actions"><button className="ghost small" disabled={!c.website_url||checking===c.client_id}',
    '</div><div className="client-score-panel"><div><span>CLIENT PERFORMANCE</span><strong>{score}/85</strong></div><div className="score-track"><i style={{width:Math.min(100,Math.round((score/85)*100))+\'%\'}}/></div><small>Logs {performance.components?.logs?.events??0} · Deployments {performance.components?.deployments?.events??0} · Audits {performance.components?.audits?.events??0} · Tokens {performance.components?.tokens?.estimated??0}</small></div><div className="inventory-actions"><button className="ghost small" disabled={!c.website_url||checking===c.client_id}'
  )
  main = main.replace(
    '<button className="danger small" onClick={()=>setRemoving(c)}>Remove Client</button>',
    '<button className="ghost small" disabled={simulating===c.client_id} onClick={()=>simulateIncident(c.client_id)}>{simulating===c.client_id?\'Creating incident…\':\'Simulate client incident\'}</button><button className="danger small" onClick={()=>setRemoving(c)}>Remove Client</button>'
  )
  main = main.replace(
    '</article>})}{!clients.length',
    '</article>})}{!clients.length'
  )
  fs.writeFileSync(path, main)
}

const cssPath = 'src/style.css'
let css = fs.readFileSync(cssPath, 'utf8')
if (!css.includes('.client-score-panel')) {
  css += `\n.client-score-panel{grid-column:1/-1;border:1px solid var(--border);border-radius:14px;padding:12px 14px;background:var(--card)}.client-score-panel>div:first-child{display:flex;justify-content:space-between;align-items:center}.client-score-panel span{font-size:10px;letter-spacing:.12em;color:var(--muted);font-weight:800}.client-score-panel strong{font-size:20px}.score-track{height:6px;border-radius:999px;background:var(--border);overflow:hidden;margin:9px 0}.score-track i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#06b6d4,#14b8a6)}.client-score-panel small{color:var(--muted);font-size:10px}\n`
  fs.writeFileSync(cssPath, css)
}
