import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const stylePath = path.join(root, 'src', 'style.css')
const marker = '/* TRACEGAURD AUDIT UI v1 */'

let css = fs.readFileSync(stylePath, 'utf8')
if (!css.includes(marker)) {
  css += `

${marker}
.audit-list{padding:0;overflow:hidden}
.audit-row{position:relative;display:grid;grid-template-columns:minmax(190px,.85fr) minmax(150px,.8fr) minmax(150px,.75fr) minmax(260px,1.6fr);gap:16px;align-items:center;margin:0;padding:17px 20px 17px 34px;border:0;border-bottom:1px solid var(--line);border-left:0;background:linear-gradient(90deg,rgba(88,230,223,.035),transparent 55%);transition:background .2s ease,transform .2s ease}
.audit-row:last-child{border-bottom:0}
.audit-row:hover{background:linear-gradient(90deg,rgba(88,230,223,.10),rgba(88,230,223,.025));transform:translateX(2px)}
.audit-row:before{content:'';position:absolute;left:15px;top:50%;width:8px;height:8px;transform:translateY(-50%);border-radius:50%;background:var(--cyan);box-shadow:0 0 0 4px rgba(88,230,223,.08),0 0 14px rgba(88,230,223,.35)}
.audit-row>span{font:500 10px/1.45 'Space Grotesk';color:#8da4af;letter-spacing:.02em}
.audit-row>b{display:inline-flex;align-items:center;justify-content:flex-start;width:max-content;max-width:100%;padding:7px 10px;border:1px solid #28515c;border-radius:8px;background:#102630;color:#c8f7f3;font:700 9px/1.2 'DM Sans';letter-spacing:.10em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.audit-row>small{display:block;min-width:0;color:#9aadb6;font:500 10px/1.45 'DM Sans';overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.audit-row>code{display:block;min-width:0;max-height:58px;overflow:auto;padding:9px 11px;border:1px solid #203a46;border-radius:8px;background:#08141c;color:#78939e;font:500 9px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
.audit-row>code::-webkit-scrollbar{width:5px;height:5px}.audit-row>code::-webkit-scrollbar-thumb{background:#274652;border-radius:8px}
@media(max-width:1050px){.audit-row{grid-template-columns:1fr 1fr}.audit-row>code{grid-column:1/-1}.audit-row>small{justify-self:start}}
@media(max-width:650px){.audit-row{grid-template-columns:1fr;gap:8px;padding-left:30px}.audit-row>code{grid-column:auto}.audit-row>b{width:100%}}
`
  fs.writeFileSync(stylePath, css)
}
