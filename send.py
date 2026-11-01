import os, json, requests

T, C = os.environ["TG_TOKEN"], os.environ["TG_CHAT"]
API = f"https://api.telegram.org/bot{T}"

media = [{"type": "photo", "media": "attach://a"},
         {"type": "photo", "media": "attach://b"}]
r = requests.post(f"{API}/sendMediaGroup",
                  data={"chat_id": C, "media": json.dumps(media)},
                  files={"a": open("out/slide1.png", "rb"),
                         "b": open("out/slide2.png", "rb")})
print(r.text)
r.raise_for_status()

cap = open("out/caption.txt", encoding="utf-8").read()
requests.post(f"{API}/sendMessage", data={"chat_id": C, "text": cap})
