import fs from 'node:fs'
const p='src/main.tsx'
let s=fs.readFileSync(p,'utf8')
const target="{view==='Clients'&&<Clients clients={clients} token={token!} onChanged={load} onIncident={analyze}/> }"
const target2="{view==='Clients'&&<Clients clients={clients} token={token!} onChanged={load} onIncident={analyze}/>}"
const replacement="{view==='Clients'&&<ClientManagement clients={clients} token={token!} onChanged={load} onIncident={analyze}/>}"
s=s.replace(target,replacement).replace(target2,replacement)
fs.writeFileSync(p,s)
