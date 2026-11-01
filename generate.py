import yfinance as yf, mplfinance as mpf, random, json, time, os
import matplotlib
matplotlib.use("Agg")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X"]
SHOW, HIDE = 60, 24
TOTAL = SHOW + HIDE

pair = random.choice(PAIRS)
df = yf.download(pair, period="700d", interval="1h", progress=False, auto_adjust=True)
df.columns = df.columns.get_level_values(0)
df = df[["Open","High","Low","Close"]].dropna()

for _ in range(200):
    i = random.randint(0, len(df) - TOTAL)
    w = df.iloc[i:i+TOTAL]
    if (w.index[-1] - w.index[0]).days <= 6:
        break

lo, hi = w["Low"].min(), w["High"].max()
pad = (hi - lo) * 0.15

def draw(data, path, title, color, extra=None):
    fig, axes = mpf.plot(data, type="candle", style="nightclouds",
                         returnfig=True, figsize=(10.8, 13.5), axisoff=True)
    ax = axes[0]
    ax.set_xlim(-1, TOTAL)
    ax.set_ylim(lo - pad, hi + pad * 1.5)
    fig.text(0.5, 0.92, title, color=color, fontsize=52,
             ha="center", weight="bold")
    if extra:
        ax.axvline(SHOW - 0.5, color="white", linestyle="--", alpha=0.6)
        fig.text(0.5, 0.86, extra, color="white", fontsize=30, ha="center")
    fig.savefig(path, dpi=100)

pip = 0.01 if "JPY" in pair else 0.0001
diff = (w["Close"].iloc[-1] - w["Close"].iloc[SHOW-1]) / pip
up = diff > 0

os.makedirs("out", exist_ok=True)
p1, p2 = "out/slide1.png", "out/slide2.png"

draw(w.iloc[:SHOW], p1, "UP or DOWN?", "#ffd54f")
draw(w, p2, "UP ▲" if up else "DOWN ▼",
     "#00e676" if up else "#ff5252", f"{abs(diff):.0f} pips in 24 hours")

caption = ("بالا میره یا پایین؟ 👆👇\n"
           "حدستو کامنت کن، بعد برو اسلاید بعدی ✅\n"
           "هر روز یه چالش جدید 🔥 فالو کن\n\n"
           "⚠️ محتوای آموزشی/سرگرمیه و توصیه مالی نیست.\n"
           "#فارکس #تحلیل_تکنیکال #forex #trading #chart")
open("out/caption.txt", "w", encoding="utf-8").write(caption)
