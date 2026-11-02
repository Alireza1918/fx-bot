import yfinance as yf, mplfinance as mpf, pandas as pd, random, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"

PAGE = "@market_made.ir"
DISPLAY_TZ = "Asia/Tehran"
SYMBOLS = ["XAUUSD=X", "GC=F"]
CONFIG = {"1m": dict(period="7d", interval="1m"),
          "5m": dict(period="60d", interval="5m")}
STEP = {"1m": 1, "5m": 5}
IMP, PAUSE, HIDE = 50, 12, 25
SHOW = IMP + PAUSE
TOTAL = SHOW + HIDE
SESS_FA = {"ASIA": "آسیا", "LONDON": "لندن",
           "LONDON/NY OVERLAP": "لندن و نیویورک", "NEW YORK": "نیویورک"}
SESS_EN = {"ASIA": "ASIA", "LONDON": "LONDON",
           "LONDON/NY OVERLAP": "LONDON/NY", "NEW YORK": "NEW YORK"}
GREEN, RED, YELLOW = "#26a69a", "#ef5350", "#ffd54f"
BG = "#0e1117"


def session_of(h):
    if 7 <= h < 12:
        return "LONDON"
    if 12 <= h < 16:
        return "LONDON/NY OVERLAP"
    if 16 <= h < 21:
        return "NEW YORK"
    return "ASIA"


def load(tf):
    for sym in SYMBOLS:
        try:
            df = yf.download(sym, progress=False, auto_adjust=True, **CONFIG[tf])
            if df is None or len(df) < 300:
                continue
            df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close"]].dropna()
            idx = df.index
            if idx.tz is not None:
                idx = idx.tz_convert("UTC").tz_localize(None)
            df.index = idx
            if len(df) >= 300:
                return df
        except Exception as e:
            print("load error", sym, tf, e)
    return None


def analyze(w, avg, mult):
    imp, pause, post = w.iloc[:IMP], w.iloc[IMP:SHOW], w.iloc[SHOW:]
    net = imp["Close"].iloc[-1] - imp["Close"].iloc[0]
    rng = imp["High"].max() - imp["Low"].min()
    if rng == 0 or abs(net) < mult * avg:
        return None
    eff = abs(net) / rng
    if eff < 0.55:
        return None
    d0 = 1 if net > 0 else -1
    # بخش آخر حرکت هم باید تند باشه
    last = imp.iloc[-15:]
    if (last["Close"].iloc[-1] - last["Close"].iloc[0]) * d0 < 0.4 * abs(net):
        return None
    # مکث کوتاه و فشرده
    ph, pl = pause["High"].max(), pause["Low"].min()
    if (ph - pl) > 0.45 * abs(net):
        return None
    cl = post["Close"].values
    ref = imp["Close"].iloc[-1]
    moved = (cl[-1] - pause["Close"].iloc[-1])
    if abs(moved) < 0.35 * abs(net):
        return None
    big = int(((imp["Close"] - imp["Open"]).abs() > 1.5 * avg).sum())
    score = 5 * eff + abs(net) / (avg * 10) + big / 10 + abs(moved) / abs(net)
    return dict(net=net, moved=moved, eff=eff, score=score,
                cont=((moved > 0) == (net > 0)))


def pick(df, tf):
    avg = (df["High"] - df["Low"]).mean()
    for mult in (14, 10, 7):
        out = []
        for i in range(0, len(df) - TOTAL, 2):
            w = df.iloc[i:i + TOTAL]
            span = (w.index[-1] - w.index[0]).total_seconds() / 60
            if span > TOTAL * STEP[tf] * 1.5:
                continue
            a = analyze(w, avg, mult)
            if a:
                out.append((i, a, session_of(w.index[SHOW - 1].hour)))
        if out:
            sess = random.choice(sorted({o[2] for o in out}))
            pool = sorted([o for o in out if o[2] == sess],
                          key=lambda o: -o[1]["score"])
            pool = pool[:max(1, len(pool) // 3)]
            i, a, _ = random.choice(pool)
            return i, a
    return None


tfs = ["1m", "5m"]
random.shuffle(tfs)
chosen = None
for tf in tfs:
    df = load(tf)
    if df is None:
        continue
    r = pick(df, tf)
    if r:
        i, a = r
        chosen = (tf, df.iloc[i:i + TOTAL], a)
        break

if not chosen:
    print("no setup found")
    sys.exit(1)

tf, w, a = chosen
shown = w.iloc[:SHOW]
sess = session_of(w.index[SHOW - 1].hour)
t_local = pd.DatetimeIndex([w.index[SHOW - 1]]).tz_localize("UTC").tz_convert(DISPLAY_TZ)[0]

p_start = w["Close"].iloc[SHOW - 1]
p_end = w["Close"].iloc[-1]
up = p_end > p_start
col = GREEN if up else RED

lo2, hi2 = w["Low"].min(), w["High"].max()
pad = (hi2 - lo2) * 0.06
YLIM = (lo2 - pad, hi2 + pad)

RECT = [0.02, 0.14, 0.86, 0.70]
mc = mpf.make_marketcolors(up=GREEN, down=RED, edge="inherit",
                           wick="inherit", inherit=True)
STYLE = mpf.make_mpf_style(marketcolors=mc, facecolor=BG, figcolor=BG,
                           edgecolor="#2a2f3a", gridcolor="#1c212b",
                           gridstyle="-", y_on_right=True)


def tlabels(index, step=12):
    t = pd.DatetimeIndex(index).tz_localize("UTC").tz_convert(DISPLAY_TZ)
    pos = list(range(0, len(t), step))
    return pos, [t[p].strftime("%H:%M") for p in pos]


def draw(data, path, title, tcolor, sub, extra=None, footer=None, result=False):
    fig, axes = mpf.plot(data, type="candle", style=STYLE, ylabel="",
                         returnfig=True, figsize=(10.8, 13.5))
    for ax_ in axes:
        ax_.set_position(RECT)
    ax = axes[0]
    ax.set_xlim(-1, TOTAL)
    ax.set_ylim(*YLIM)
    pos, labs = tlabels(data.index)
    ax.set_xticks(pos)
    ax.set_xticklabels(labs, color="#9aa3b2", fontsize=18, rotation=0)
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", labelsize=18, labelcolor="#9aa3b2", length=0)
    ax.tick_params(axis="x", length=0, pad=10)
    for s in ax.spines.values():
        s.set_visible(False)

    last = data["Close"].iloc[-1]
    lcol = col if result else YELLOW
    ax.axhline(last, color=lcol, linestyle="--", linewidth=1, alpha=0.7)
    ax.text(1.0, last, f" {last:.2f} ", transform=ax.get_yaxis_transform(),
            ha="left", va="center", color="black", fontsize=18, weight="bold",
            bbox=dict(fc=lcol, ec="none"), clip_on=False, zorder=10)

    if result:
        ax.axvspan(SHOW - 0.5, TOTAL, color=col, alpha=0.08)
        ax.axvline(SHOW - 0.5, color="white", linestyle="--", alpha=0.5)

    fig.text(0.5, 0.95, title, color=tcolor, fontsize=62,
             ha="center", va="center", weight="bold")
    fig.text(0.5, 0.905, sub, color="#9aa3b2", fontsize=28,
             ha="center", va="center")
    if extra:
        fig.text(0.5, 0.87, extra, color=tcolor, fontsize=30,
                 ha="center", va="center", weight="bold")
    if footer:
        fig.text(0.5, 0.07, footer, color=YELLOW, fontsize=28,
                 ha="center", va="center", weight="bold")
    fig.text(0.5, 0.032, PAGE, color="#6b7280", fontsize=22,
             ha="center", va="center")
    fig.savefig(path, dpi=100, facecolor=BG)


sub = f"XAUUSD  |  {tf.upper()}  |  {SESS_EN[sess]} SESSION"

os.makedirs("out", exist_ok=True)
draw(shown, "out/slide1.png", "UP or DOWN?", YELLOW, sub,
     footer="Do your own analysis")
draw(w, "out/slide2.png", "UP ▲" if up else "DOWN ▼", col, sub,
     extra=f"{p_start:.2f}  →  {p_end:.2f}",
     footer="Comment your analysis", result=True)

caption = (f"طلا (XAUUSD) | تایم‌فریم {STEP[tf]} دقیقه ⏱\n"
          f"سشن: {SESS_FA[sess]} | ساعت: {t_local.strftime('%H:%M')} (وقت تهران)\n\n"
          "بعد از یه حرکت تند، قیمت یه مکث کرده 🚀\n"
          "از اینجا بالا میره یا پایین؟ 👆👇\n\n"
          "✍️ حدست رو با دلیل بنویس\n"
          "📸 یا عکس تحلیل خودت رو کامنت کن\n"
          "بعد برو اسلاید دوم و جواب رو ببین ✅\n"
          "بهترین تحلیل رو پین می‌کنم 📌\n\n"
          "⚠️ محتوای آموزشی/سرگرمیه و توصیه مالی نیست.\n"
          "#طلا #فارکس #xauusd #gold #پرایس_اکشن #تحلیل_تکنیکال #forex #trading")

dir_fa = "بالا" if up else "پایین"
kind_fa = "ادامه‌ی حرکت قبلی" if a["cont"] else "برگشت"
answer = (f"✅ جواب: قیمت {dir_fa} رفت.\n"
          f"از {p_start:.2f} شروع شد و به {p_end:.2f} رسید.\n\n"
          "نکات برای کامنت پین‌شده:\n"
          f"• قبل از مکث یه حرکت {'صعودی' if a['net'] > 0 else 'نزولی'} تند و تمیز بود.\n"
          f"• بعد از مکث کوتاه، قیمت {dir_fa} رفت ({kind_fa}).\n\n"
          "شما چی دیده بودید؟ 👇")

open("out/caption.txt", "w", encoding="utf-8").write(caption + "\n-----\n" + answer)
from PIL import Image
for p in ("out/slide1.png", "out/slide2.png"):
    print(p, Image.open(p).size)
