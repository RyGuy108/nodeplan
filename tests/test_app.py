import sys, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
VEND = os.path.join(HERE, "vendor", "node_modules")
from playwright.sync_api import sync_playwright

HTML = os.path.join(HERE, "..", "index.html")
D3 = open(os.path.join(VEND, "d3/dist/d3.min.js")).read()
errors = []
SHOTS = os.path.join(HERE, "screenshots"); os.makedirs(SHOTS, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 860})
    pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append("CONSOLE " + m.text))
    pg.route("**/d3.min.js", lambda r: r.fulfill(body=D3, content_type="application/javascript"))
    pg.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(body="", content_type="text/css"))
    pg.goto("file://" + os.path.abspath(HTML))
    pg.wait_for_timeout(1500)
    pg.screenshot(path=os.path.join(SHOTS, "s1_graph.png"))
    print("nodes:", pg.eval_on_selector_all("g.node", "e=>e.length"), "links:", pg.eval_on_selector_all("path.link", "e=>e.length"))

    # parser checks
    r = pg.evaluate("""()=>{
      const cases=['Essay draft fri 3pm p1 #Writing ~90m after:outline','Call mom tomorrow at 5:30pm','Standup 10-10:15am event!','Read ch 5 nov 12 !! @school ~1.5h','Gym in 3 days','Pay rent 12/1','plain task'];
      return cases.map(c=>{const q=parseQuick(c);return [c,q.title,q.due,q.time,q.end,q.priority,q.project,q.estimate,q.labels,q.after,q.kind]})}""")
    for x in r: print(x)

    # quick add
    pg.fill("#qa", "Outline essay tomorrow p2 #Writing ~30m")
    pg.press("#qa", "Enter")
    pg.fill("#qa", "Essay draft fri p1 #Writing ~90m after:outline")
    pg.press("#qa", "Enter")
    pg.wait_for_timeout(600)
    print("deps of essay:", pg.evaluate("()=>{const t=S.tasks.find(t=>t.title==='Essay draft');return t.deps.map(id=>byId(id).title)}"))
    pg.screenshot(path=os.path.join(SHOTS, "s2_added.png"))

    # layouts
    pg.click("#layoutSeg button[data-l=flow]"); pg.wait_for_timeout(900); pg.screenshot(path=os.path.join(SHOTS, "s3_flow.png"))
    pg.click("#layoutSeg button[data-l=time]"); pg.wait_for_timeout(900); pg.screenshot(path=os.path.join(SHOTS, "s4_time.png"))
    pg.click("#layoutSeg button[data-l=web]"); pg.wait_for_timeout(900)

    # list view
    pg.click("#viewSeg button[data-v=list]"); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(SHOTS, "s5_list.png"))
    pg.click(".row >> nth=1"); pg.wait_for_timeout(200); pg.screenshot(path=os.path.join(SHOTS, "s6_detail.png"))
    pg.click(".row >> nth=1 >> .chk"); pg.wait_for_timeout(200)

    # imports
    ics = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:abc\r\nSUMMARY:Weekly sync\r\nDTSTART:20250106T150000Z\r\nDTEND:20250106T160000Z\r\nRRULE:FREQ=WEEKLY;BYDAY=MO,TH\r\nEND:VEVENT\r\nBEGIN:VTODO\r\nUID:t1\r\nSUMMARY:File taxes\r\nDUE;VALUE=DATE:20261201\r\nPRIORITY:1\r\nEND:VTODO\r\nEND:VCALENDAR"
    n = pg.evaluate("(t)=>importText(t,'cal.ics')", ics)
    print("ics imported:", n, pg.evaluate("()=>S.tasks.filter(t=>t.source==='calendar').length"))
    n2 = pg.evaluate("(t)=>importText(t,'cal.ics')", ics)
    print("ics reimport (should not grow):", pg.evaluate("()=>S.tasks.filter(t=>t.source==='calendar').length"))
    csv = 'Content,Priority,Due Date,Project\n"Buy milk, eggs",1,2026-11-20,Errands\nWash car,3,next week,Errands\n'
    print("csv:", pg.evaluate("(t)=>importText(t,'todo.csv')", csv))
    md = "# Trip\n- [ ] Book flights 📅 2026-12-01 ⏫\n  - [ ] Compare prices ~20m\n- [x] Renew passport\n- [ ] Pack after:flights\n"
    print("md:", pg.evaluate("(t)=>importText(t,'trip.md')", md))
    print(pg.evaluate("()=>S.tasks.filter(t=>t.project==='Trip').map(t=>[t.title,t.due,t.priority,t.done,t.parent&&byId(t.parent).title,t.deps.map(d=>byId(d).title)])"))
    trello = json.dumps({"name": "Board", "lists": [{"id": "l1", "name": "To do"}], "cards": [{"id": "c1", "name": "Card A", "idList": "l1", "due": "2026-11-15T17:00:00.000Z", "desc": ""}], "checklists": [{"idCard": "c1", "checkItems": [{"id": "i1", "name": "step", "state": "incomplete"}]}]})
    print("trello:", pg.evaluate("(t)=>importText(t,'b.json')", trello))
    pg.click("#viewSeg button[data-v=graph]"); pg.wait_for_timeout(1200)

    # timer
    pg.evaluate("()=>{const t=S.tasks.find(t=>t.title==='Outline essay');startFocusOn(t.id,true)}")
    pg.wait_for_timeout(1300)
    pg.screenshot(path=os.path.join(SHOTS, "s7_focus.png"))
    # simulate finishing: set endsAt in past with a 25-minute segment
    pg.evaluate("()=>{T.segStart=Date.now()-25*60e3;T.sessStart=T.segStart;T.endsAt=Date.now()-10}")
    pg.wait_for_timeout(600)
    print("after finish:", pg.evaluate("()=>[T.phase,T.running,T.cycle,S.sessions.length,Math.round(trackedMap()[T.taskId]/60)]"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    # switch to stopwatch
    pg.evaluate("()=>{tPause();setMode('sw');tStart()}"); pg.wait_for_timeout(1200)
    print("sw elapsed:", pg.evaluate("()=>tElapsed().toFixed(1)"))
    pg.evaluate("()=>{T.segStart-=120e3;tReset()}")
    print("sessions:", pg.evaluate("()=>S.sessions.map(s=>[s.mode,s.secs])"))
    pg.evaluate("()=>{setMode('cd')}");
    pg.evaluate("()=>openFocus()"); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(SHOTS, "s8_cd.png"))
    pg.keyboard.press("Escape")
    pg.evaluate("()=>openDrawer()"); pg.wait_for_timeout(400); pg.screenshot(path=os.path.join(SHOTS, "s9_drawer.png"))
    pg.evaluate("()=>closeDrawer()")
    # exports
    print(pg.evaluate("()=>exportICS().split('\\r\\n').length"), pg.evaluate("()=>exportMD().slice(0,200)"))
    # dark theme
    pg.evaluate("()=>{S.settings.theme='dark';applyTheme();setFilter({t:'smart',v:'all'})}"); pg.wait_for_timeout(1500)
    pg.screenshot(path=os.path.join(SHOTS, "s10_dark.png"))
    # reload persistence
    pg.reload(); pg.wait_for_timeout(1200)
    print("after reload tasks:", pg.evaluate("()=>S.tasks.length"), "demo", pg.evaluate("()=>S.demo"))
    # mobile
    pg.set_viewport_size({"width": 390, "height": 800}); pg.wait_for_timeout(600); pg.screenshot(path=os.path.join(SHOTS, "s11_mobile.png"))
    b.close()

print("ERRORS:", errors)

# ---------- round 2: attachments, pressing, zip ----------
import tempfile, zipfile, datetime
TMP = tempfile.mkdtemp()
tom = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y%m%d")
def ics(uid, name): return f"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:{uid}\r\nSUMMARY:{name}\r\nLOCATION:https://zoom.us/j/123\r\nDTSTART:{tom}T180000Z\r\nDTEND:{tom}T190000Z\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
open(f"{TMP}/cal1.ics","w").write(ics("z1","Office hours"))
with zipfile.ZipFile(f"{TMP}/gcal.zip","w") as z:
    z.writestr("me.ical/cal1.ics", ics("z1","Office hours")); z.writestr("me.ical/cal2.ics", ics("z2","Lab"))
import struct, zlib
def png(path, w=64, h=40):
    raw = b"".join(b"\x00" + bytes([70,120,200])*w for _ in range(h))
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t+d) & 0xffffffff)
    open(path,"wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b""))
png(f"{TMP}/shot.png")
JSZ = open(os.path.join(VEND, "jszip/dist/jszip.min.js")).read()
errors2 = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 860})
    pg.on("pageerror", lambda e: errors2.append("PAGEERROR " + str(e)))
    pg.route("**/d3.min.js", lambda r: r.fulfill(body=D3, content_type="application/javascript"))
    pg.route("**/jszip.min.js", lambda r: r.fulfill(body=JSZ, content_type="application/javascript"))
    pg.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(body="", content_type="text/css"))
    pg.goto("file://" + os.path.abspath(HTML)); pg.wait_for_timeout(1200)
    pg.evaluate("()=>{localStorage.clear()}"); pg.reload(); pg.wait_for_timeout(1200)
    print("pressing:", pg.evaluate("()=>pressList().map(x=>[x.t.title,x.lvl,x.why])"))
    pg.evaluate("()=>{const t=S.tasks.find(t=>t.title==='Write About page');t.due=isoPlus(-2);commit()}"); pg.wait_for_timeout(1500)
    pg.screenshot(path=os.path.join(SHOTS, "r1_press_graph.png"))
    # attach via file input on selected task
    pg.evaluate("()=>select(S.tasks.find(t=>t.title==='Problem set 6').id)"); pg.wait_for_timeout(200)
    pg.set_input_files("[data-attfile]", [f"{TMP}/shot.png", f"{TMP}/cal1.ics"]); pg.wait_for_timeout(1500)
    pg.click("[data-attform=link]"); pg.fill("#afUrl", "https://claude.ai/artifact/abc123"); pg.press("#afUrl", "Enter"); pg.wait_for_timeout(300)
    pg.click("[data-attform=note]"); pg.fill("#afText", "Submitted on Canvas 4:52pm, confirmation #A1B2"); pg.click("[data-attsave=note]"); pg.wait_for_timeout(300)
    print("atts:", pg.evaluate("()=>byId(UI.selected).attachments.map(a=>[a.kind,a.name,!!a.inline,a.size])"))
    pg.screenshot(path=os.path.join(SHOTS, "r2_attach.png"))
    pg.click(".att.img"); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(SHOTS, "r3_lightbox.png")); pg.keyboard.press("Escape")
    # zip import
    pg.evaluate("()=>openDrawer()")
    pg.set_input_files("#fileIn", f"{TMP}/gcal.zip"); pg.wait_for_timeout(1500)
    print("zip events:", pg.evaluate("()=>S.tasks.filter(t=>t.title==='Office hours'||t.title==='Lab').map(t=>[t.title,t.due,t.time,t.attachments.map(a=>a.url)])"))
    pg.click("[data-howto='Google Calendar']"); pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(SHOTS, "r4_howto.png"))
    pg.evaluate("()=>closeDrawer()")
    pg.click("#viewSeg button[data-v=list]"); pg.wait_for_timeout(400); pg.screenshot(path=os.path.join(SHOTS, "r5_list.png"))
    pg.evaluate("()=>{select(null);setView('graph')}"); pg.wait_for_timeout(1200)
    pg.screenshot(path=os.path.join(SHOTS, "r6_graph.png"))
    pg.reload(); pg.wait_for_timeout(1200)
    print("persist atts:", pg.evaluate("()=>S.tasks.find(t=>t.title==='Problem set 6').attachments.length"), "blob ok:", pg.evaluate("()=>{const a=S.tasks.find(t=>t.title==='Problem set 6').attachments.find(a=>a.kind==='image');return !!attURL(a)||'loading'}"))
    pg.screenshot(path=os.path.join(SHOTS, "readme_shot.png"))
    b.close()
print("ERRORS2:", errors2)
sys.exit(1 if errors or errors2 else 0)
