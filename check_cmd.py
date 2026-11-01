import os, requests

T, C = os.environ["TG_TOKEN"], str(os.environ["TG_CHAT"])
API = f"https://api.telegram.org/bot{T}"

ups = requests.get(f"{API}/getUpdates", timeout=30).json().get("result", [])
go = False
for u in ups:
    m = u.get("message") or {}
    if str(m.get("chat", {}).get("id")) != C:
        continue
    t = (m.get("text") or "").strip().lower()
    if t.startswith("/new") or "تعویض" in t:
        go = True

if ups:
    requests.get(f"{API}/getUpdates",
                 params={"offset": ups[-1]["update_id"] + 1}, timeout=30)

if go:
    requests.post(f"{API}/sendMessage",
                  data={"chat_id": C, "text": "⏳ چارت جدید در حال ساخته شدنه..."})

with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"go={'true' if go else 'false'}\n")
