"""Local read-only paper portfolio dashboard. No orders or secrets."""
import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from urllib.parse import urlparse
from .storage import Store

def snapshot(store):
    p = store.load()
    equity = p.equity(p.last_prices)
    positions = []
    for symbol, pos in sorted(p.positions.items()):
        price = p.last_prices.get(symbol, pos.entry)
        positions.append({"symbol": symbol, "quantity": pos.quantity,
                          "entry": pos.entry, "last": price, "stop": pos.stop,
                          "target": pos.target, "unrealized_pnl": (price - pos.entry) * pos.quantity})
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "PAPER_ONLY", "cash": p.cash, "equity": equity,
            "realized_pnl_today": p.realized_pnl_today,
            "unrealized_pnl": sum(x["unrealized_pnl"] for x in positions),
            "halted": p.halted, "session_date": p.session_date,
            "positions": positions, "events": p.events[-100:]}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Claude — Paper Dashboard</title>
<style>
body{font:15px system-ui,sans-serif;background:#0b1220;color:#e2e8f0;margin:0;padding:25px}
main{max-width:1100px;margin:auto}h1{font-size:27px}small{color:#94a3b8}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.card{background:#17243a;border:1px solid #334155;border-radius:12px;padding:16px}
.value{font-size:23px;font-weight:700;margin-top:9px}table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px;border-bottom:1px solid #334155}section{margin-top:25px;overflow-x:auto}
.bad{color:#fca5a5}.good{color:#86efac}#error{color:#fca5a5}
</style></head><body><main><h1>Trading Claude <small>Paper only</small></h1>
<p id="status">Loading…</p><p id="error"></p><div class="cards" id="cards"></div>
<section><h2>Open positions</h2><table><thead><tr><th>Symbol</th><th>Shares</th><th>Entry</th><th>Last</th><th>Stop</th><th>Unrealized</th></tr></thead><tbody id="positions"></tbody></table></section>
<section><h2>Recent simulated events</h2><table><thead><tr><th>Type</th><th>Symbol</th><th>Qty</th><th>Price</th><th>Reason</th></tr></thead><tbody id="events"></tbody></table></section>
<p><small>Local read-only view. Prices may be stale. No real brokerage orders.</small></p></main>
<script>
const money=v=>Number(v||0).toLocaleString('en-US',{style:'currency',currency:'USD'});
function cell(tr,value){let td=document.createElement('td');td.textContent=String(value??'—');tr.appendChild(td)}
function rows(target,items,fields){let body=document.getElementById(target);body.replaceChildren();
for(let item of items){let tr=document.createElement('tr');for(let fn of fields)cell(tr,fn(item));body.appendChild(tr)}}
async function refresh(){
try{let res=await fetch('/api/status',{cache:'no-store'});if(!res.ok)throw Error('HTTP '+res.status);
let d=await res.json();document.getElementById('error').textContent='';
document.getElementById('status').textContent='Session: '+(d.session_date||'Not started')+' · '+(d.halted?'New entries HALTED':'New entries allowed subject to rules')+' · Updated '+new Date(d.timestamp_utc).toLocaleTimeString();
let metrics=[['Equity',money(d.equity)],['Cash',money(d.cash)],['Realized today',money(d.realized_pnl_today)],['Unrealized',money(d.unrealized_pnl)],['Positions',d.positions.length]];
let container=document.getElementById('cards');container.replaceChildren();
for(let [label,value] of metrics){let div=document.createElement('div');div.className='card';let l=document.createElement('small');l.textContent=label;let v=document.createElement('div');v.className='value';v.textContent=value;div.append(l,v);container.appendChild(div)}
rows('positions',d.positions,[x=>x.symbol,x=>x.quantity,x=>money(x.entry),x=>money(x.last),x=>money(x.stop),x=>money(x.unrealized_pnl)]);
rows('events',[...d.events].reverse().slice(0,40),[x=>x.type,x=>x.symbol,x=>x.qty,x=>x.price===undefined?'—':money(x.price),x=>x.reason]);
}catch(e){document.getElementById('error').textContent='Unable to refresh: '+e.message}}
refresh();setInterval(refresh,10000);
</script></body></html>"""

def handler_factory(store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path not in ("/", "/api/status"):
                self.send_error(404)
                return
            if path == "/":
                content, content_type = PAGE.encode("utf-8"), "text/html; charset=utf-8"
            else:
                try:
                    content = json.dumps(snapshot(store), allow_nan=False).encode("utf-8")
                except Exception:
                    self.send_error(500, "Unable to load paper portfolio")
                    return
                content_type = "application/json; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="paper.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("Dashboard binds to localhost only; no authentication is implemented")
    store = Store(args.database)
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(store))
    print(f"Paper dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
