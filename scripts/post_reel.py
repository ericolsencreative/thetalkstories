"""Daily reel publisher for thetalkstories.com + Instagram.
Reads _queue/schedule.json; for the first entry due today (Pacific) that isn't done:
 1) publishes that day's site snapshot (copies files out of _queue/<slug>/), commits, pushes
 2) waits for the video to be live on the site
 3) posts it to Instagram as a Reel via the Instagram API (IG_TOKEN secret)
Safe to re-run: progress is recorded in schedule.json."""
import json, os, sys, time, shutil, subprocess, datetime, zoneinfo, urllib.request, urllib.parse

API = "https://graph.instagram.com/v21.0"
TOKEN = os.environ["IG_TOKEN"]
SCHED = "_queue/schedule.json"
# flat names in a queue folder -> where they go on the site
MAP = {"index.html": "index.html", "stories__index.html": "stories/index.html", "sitemap.xml": "sitemap.xml",
       "page.html": "{slug}/index.html", "video.mp4": "{slug}/{slug}.mp4", "poster.jpg": "{slug}/{slug}.jpg"}

def git(*a): subprocess.run(["git", *a], check=True)
def save(s):
    json.dump(s, open(SCHED, "w"), indent=1)
def commit(msg):
    git("add", "-A"); git("commit", "-m", msg); git("push")
def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}" + ("" if method == "POST" else "?" + data.decode())
    req = urllib.request.Request(url, data=data if method == "POST" else None, method=method)
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"Instagram API error {e.code}: {e.read().decode()[:500]}")

today = datetime.datetime.now(zoneinfo.ZoneInfo("America/Los_Angeles")).date().isoformat()
force = os.environ.get("FORCE_SLUG", "").strip()
sched = json.load(open(SCHED))
due = [e for e in sched if not e.get("done") and (e["slug"] == force or (not force and e["date"] <= today))]
if not due:
    print("Nothing due", today); sys.exit(0)
e = due[0]; slug = e["slug"]; q = f"_queue/{slug}"
print("Publishing", slug)

if not e.get("site"):
    for src, dst in MAP.items():
        p = os.path.join(q, src)
        if os.path.exists(p):
            d = dst.format(slug=slug); os.makedirs(os.path.dirname(d) or ".", exist_ok=True); shutil.copy(p, d)
    e["site"] = True; save(sched); commit(f"Publish {slug} page")

url = f"https://thetalkstories.com/{slug}/{slug}.mp4"
for i in range(40):  # up to ~20 min for GitHub Pages to deploy
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30)
        if r.status == 200: break
    except Exception: pass
    time.sleep(30)
else:
    sys.exit("Video never went live at " + url)

c = call("POST", "me/media", media_type="REELS", video_url=url, caption=e["caption"], share_to_feed="true")
cid = c["id"]
for i in range(60):
    st = call("GET", cid, fields="status_code,status")
    if st.get("status_code") == "FINISHED": break
    if st.get("status_code") == "ERROR": sys.exit(f"Instagram processing error: {st}")
    time.sleep(10)
else:
    sys.exit("Instagram processing timed out")
pub = call("POST", "me/media_publish", creation_id=cid)
e["done"] = True; e["ig_media_id"] = pub.get("id"); save(sched); commit(f"Instagram posted: {slug}")
print("Posted", slug, pub)
