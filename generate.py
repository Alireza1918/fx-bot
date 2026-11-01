import yfinance as yf, mplfinance as mpf, random, os, sys
import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Rectangle

SYMBOLS = ["XAUUSD=X", "GC=F"]
CONFIG = {"1m": dict(period="7d", interval="1m"),
          "5m": dict(period="60d", interval="5m")}
STEP = {"1m": 1, "5m": 5}
IMP, CONS, HIDE = 45, 25, 30
SHOW = IMP + CONS
TOTAL = SHOW + HIDE


def load(tf):
    for sym in SYMBOLS:
        try:
            df = yf.download(sym, progress=False, auto_adjust=True, **CONFIG[tf])
            if df is None or len(df) < 300:
                continue
            df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close"]].dropna()
            if len(df) >= 300:
                return df
        except Exception as e:
            print("load error", sym, tf, e)
    return None


def find_setups(df, tf):
    avg = (df["High"] - df["Low"]).mean()
    for mult in (12, 9, 6):
        out = []
        for i in range(0, len(df) - TOTAL, 3):
            w = df.iloc[i:i + TOTAL]
            span = (w.index[-1] - w.index[0]).total_seconds() / 60
            if span > TOTAL * STEP[tf] * 1.5:
                continue
            imp, cons = w.iloc[:IMP], w.iloc[IMP:SHOW]
            net = imp["Close"].iloc[-1] - imp["Close"].iloc[0]
            rng = imp["High"].max() - imp["Low"].min()
            if rng == 0 or abs(net) < mult * avg:
                continue
            if abs(net) / rng < 0.6:
                continue
            c_hi, c_lo = cons["High"].max(), cons["Low"].min()
            if (c_hi - c_lo) > 0.45 * abs(net):
                continue
            if abs(cons["Close"].mean() - imp["Close"].iloc[-1]) > 0.25 * abs(net):
                continue
            out.append(i)
        if out:
            return out
    return []


tfs = ["1m", "5m"]
random.shuffle(tfs)
chosen = None
for tf in tfs:
    df = load(tf)
    if df is None:
        continue
    cands = find_setups(df, tf)
    if cands:
        i = random.choice(cands)
        chosen = (tf, df.iloc[i:i + TOTAL])
        break

if not chosen:
    print("no setup found")
    sys.exit(1)

tf, w = chosen
shown = w.iloc[:SHOW]
cons = w.iloc[IMP:SHOW]
c_hi, c_lo = cons["High"].max(), cons["Low"].min()

lo1, hi1 = shown["Low"].min(), shown["High"].max()
p1 = (hi1 - lo1) * 0.5
ylim1 = (lo1 - p1, hi1 + p1 * 1.6)

lo2, hi2 = w["Low"].min(), w["High"].max()
p2 = (hi2 - lo2) * 0.15
ylim2 = (lo2 - p2, hi2 + p2 * 2.5)


def draw(data, path, title, color, ylim, extra=None):
    fig, axes = mpf.plot(data, type="candle", style="nightclouds",
                         returnfig=True, figsize=(10.8, 13.5), axisoff=True)
    ax = axes[0]
    ax.set_xlim(-1, TOTAL)
    ax.set_ylim(*ylim)
    ax.add_patch(Rectangle((IMP - 0.5, c_lo), CONS, c_hi - c_lo,
                           facecolor="white", alpha=0.10, edgecolor="none"))
    fig.text(0.5, 0.93, title, color=color, fontsize=52,
             ha="center", weight="bold")
    fig.text(0.5, 0.885, f"XAUUSD  •  {tf.upper()}", color="#aaaaaa",
             fontsize=30, ha="center")
    if extra:
        ax.axvline(SHOW - 0.5, color="white", linestyle="--", alpha=0.6)
        fig.text(0.5, 0.84, extra, color="white", fontsize=30, ha="center")
    fig.savefig(path, dpi=100)


diff = w["Close"].iloc[-1] - w["Close"].iloc[SHOW - 1]
up = diff > 0

os.makedirs("out", exist_ok=True)
draw(shown, "out/slide1.png", "UP or DOWN?", "#ffd54f", ylim1)
draw(w, "out/slide2.png", "UP ▲" if up else "DOWN ▼",
     "#00e676" if up else "#ff5252", ylim2,
     f"${abs(diff):.1f} in {HIDE} candles")

caption = (f"طلا (XAUUSD) | تایم‌فریم {STEP[tf]} دقیقه ⏱\n"
           "بعد از حرکت قوی، قیمت رنج شده. 📦\n"
           "بالا میشکنه یا پایین؟ 👆👇\n"
           "حدستو کامنت کن، بعد برو اسلاید بعدی ✅\n"
           "هر روز یه چالش جدید 🔥 فالو کن\n\n"
           "⚠️ محتوای آموزشی/سرگرمیه و توصیه مالی نیست.\n"
           "#طلا #فارکس #xauusd #gold #تحلیل_تکنیکال #forex #trading")
open("out/caption.txt", "w", encoding="utf-8").write(caption)
