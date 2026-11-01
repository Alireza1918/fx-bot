import yfinance as yf, mplfinance as mpf, pandas as pd, random, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Rectangle

DISPLAY_TZ = "Asia/Tehran"
SYMBOLS = ["XAUUSD=X", "GC=F"]
CONFIG = {"1m": dict(period="7d", interval="1m"),
          "5m": dict(period="60d", interval="5m")}
STEP = {"1m": 1, "5m": 5}
IMP, CONS, HIDE = 40, 25, 35
SHOW = IMP + CONS
TOTAL = SHOW + HIDE
SESS_FA = {"ASIA": "آسیا", "LONDON": "لندن",
           "LONDON/NY OVERLAP": "هم‌پوشانی لندن و نیویورک",
           "NEW YORK": "نیویورک"}


def session_of(h):
    if 7 <= h < 12:
        return "LONDON"
    if 12 <= h < 16:
        return "LONDON/NY OVERLAP"
    if 16 <= h < 21:
        return "NEW YORK"
    return "ASIA"


def near_news(ts):
    if ts.weekday() > 4:
        return False
    m = ts.hour * 60 + ts.minute
    return any(abs(m - (hh * 60 + mm)) <= 30
               for hh, mm in [(12, 30), (13, 30), (14, 0), (15, 0), (18, 0)])


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
    imp, cons, post = w.iloc[:IMP], w.iloc[IMP:SHOW], w.iloc[SHOW:]
    net = imp["Close"].iloc[-1] - imp["Close"].iloc[0]
    rng = imp["High"].max() - imp["Low"].min()
    if rng == 0 or abs(net) < mult * avg or abs(net) / rng < 0.55:
        return None
    hi, lo = cons["High"].max(), cons["Low"].min()
    h = hi - lo
    if h < 2 * avg or h > 0.5 * abs(net):
        return None
    if abs(cons["Close"].mean() - imp["Close"].iloc[-1]) > 0.3 * abs(net):
        return None
    top = int((cons["High"] >= hi - 0.15 * h).sum())
    bot = int((cons["Low"] <= lo + 0.15 * h).sum())
    if top < 2 or bot < 2:
        return None
    cl = post["Close"].values
    out = np.where((cl > hi) | (cl < lo))[0]
    if len(out) == 0:
        return None
    k = int(out[0])
    if k > 15:
        return None
    d = 1 if cl[k] > hi else -1
    level = hi if d == 1 else lo
    if (cl[k] - level) * d < 0.1 * h:
        return None
    if (cl[-1] - level) * d < 0.5 * h:
        return None
    rt = None
    for j in range(k + 1, min(k + 13, len(post))):
        c = post.iloc[j]
        if d == 1 and c["Low"] <= hi + 0.15 * h and c["Close"] >= hi:
            rt = j
            break
        if d == -1 and c["High"] >= lo - 0.15 * h and c["Close"] <= lo:
            rt = j
            break
    target = level + d * h
    reached = (post["High"].max() >= target) if d == 1 else (post["Low"].min() <= target)
    body = abs(post["Close"].iloc[k] - post["Open"].iloc[k])
    avgb = (cons["Close"] - cons["Open"]).abs().mean()
    ratio = body / avgb if avgb > 0 else 0
    return dict(net=net, hi=hi, lo=lo, h=h, top=top, bot=bot, k=k, d=d,
                rt=rt, target=target, reached=bool(reached), ratio=ratio,
                cont=(d == (1 if net > 0 else -1)))


def pick(df, tf):
    avg = (df["High"] - df["Low"]).mean()
    for mult in (10, 7, 5):
        out = []
        for i in range(0, len(df) - TOTAL, 2):
            w = df.iloc[i:i + TOTAL]
            span = (w.index[-1] - w.index[0]).total_seconds() / 60
            if span > TOTAL * STEP[tf] * 1.5:
                continue
            a = analyze(w, avg, mult)
            if a:
                out.append((i, a, session_of(w.index[IMP].hour)))
        if out:
            sess = random.choice(sorted({o[2] for o in out}))
            i, a, _ = random.choice([o for o in out if o[2] == sess])
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
hi, lo, h, d, k = a["hi"], a["lo"], a["h"], a["d"], a["k"]
shown = w.iloc[:SHOW]
bx = SHOW + k
by = w["Close"].iloc[bx]
level = hi if d == 1 else lo
sess = session_of(w.index[IMP].hour)
news = near_news(w.index[SHOW + k])
t_local = pd.DatetimeIndex([w.index[IMP]]).tz_localize("UTC").tz_convert(DISPLAY_TZ)[0]

lo1, hi1 = shown["Low"].min(), shown["High"].max()
p1 = (hi1 - lo1) * 0.5
ylim1 = (lo1 - p1, hi1 + p1 * 1.6)

lo2 = min(w["Low"].min(), a["target"])
hi2 = max(w["High"].max(), a["target"])
p2 = (hi2 - lo2) * 0.1
ylim2 = (lo2 - p2, hi2 + p2)

RECT1 = [0.03, 0.14, 0.84, 0.70]
RECT2 = [0.03, 0.40, 0.84, 0.44]

STYLE = mpf.make_mpf_style(base_mpf_style="nightclouds", gridstyle=":",
                           gridcolor="#2a2a2a", y_on_right=True)


def tlabels(index, step=10):
    t = pd.DatetimeIndex(index).tz_localize("UTC").tz_convert(DISPLAY_TZ)
    pos = list(range(0, len(t), step))
    return pos, [t[p].strftime("%H:%M") for p in pos]


def draw(data, path, title, color, ylim, rect, sub, extra=None,
         lines=None, footer=None, analysis=False):
    fig, axes = mpf.plot(data, type="candle", style=STYLE, ylabel="",
                         returnfig=True, figsize=(10.8, 13.5))
    for ax_ in axes:
        ax_.set_position(rect)
    ax = axes[0]
    ax.set_xlim(-1, TOTAL)
    ax.set_ylim(*ylim)
    pos, labs = tlabels(data.index)
    ax.set_xticks(pos)
    ax.set_xticklabels(labs, color="#cccccc", fontsize=17)
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", labelsize=17, labelcolor="#cccccc")
    ax.add_patch(Rectangle((IMP - 0.5, lo), CONS, h,
                           facecolor="white", alpha=0.10, edgecolor="none"))
    last = data["Close"].iloc[-1]
    ax.axhline(last, color="#ffd54f", linestyle="--", linewidth=1, alpha=0.7)
    ax.text(1.0, last, f" {last:.2f} ", transform=ax.get_yaxis_transform(),
            ha="left", va="center", color="black", fontsize=17, weight="bold",
            bbox=dict(fc="#ffd54f", ec="none"), clip_on=False, zorder=10)
    fig.text(0.5, 0.95, title, color=color, fontsize=52,
             ha="center", weight="bold")
    fig.text(0.5, 0.91, sub, color="#aaaaaa", fontsize=26, ha="center")
    if extra:
        fig.text(0.5, 0.87, extra, color="white", fontsize=28, ha="center")
    if analysis:
        ax.axvline(SHOW - 0.5, color="white", linestyle="--", alpha=0.5)
        ax.hlines(hi, IMP - 0.5, TOTAL, colors="#ff5252", linewidth=2, alpha=0.9)
        ax.hlines(lo, IMP - 0.5, TOTAL, colors="#00e676", linewidth=2, alpha=0.9)
        ax.text(TOTAL - 1, hi, "RESISTANCE", color="#ff5252", fontsize=18,
                ha="right", va="bottom")
        ax.text(TOTAL - 1, lo, "SUPPORT", color="#00e676", fontsize=18,
                ha="right", va="top")
        ax.hlines(a["target"], SHOW - 0.5, TOTAL, colors="#ffd54f",
                  linestyles=":", linewidth=2)
        ax.text(TOTAL - 1, a["target"], "TARGET", color="#ffd54f", fontsize=18,
                ha="right", va="bottom" if d == 1 else "top")
        ax.annotate("BREAKOUT", xy=(bx, by),
                    xytext=(max(bx - 14, 2), by + d * 0.9 * h),
                    color="white", fontsize=20, weight="bold",
                    arrowprops=dict(arrowstyle="->", color="yellow", lw=2.5),
                    bbox=dict(boxstyle="round", fc="#111111", ec="yellow"))
        if a["rt"] is not None:
            rx = SHOW + a["rt"]
            ax.annotate("RETEST", xy=(rx, level),
                        xytext=(rx + 1, level - d * 1.0 * h),
                        color="white", fontsize=18, weight="bold",
                        arrowprops=dict(arrowstyle="->", color="cyan", lw=2),
                        bbox=dict(boxstyle="round", fc="#111111", ec="cyan"))
    if lines:
        y = 0.33
        for n, t in enumerate(lines):
            fig.text(0.05, y, t, color="#ffd54f" if n == 0 else "white",
                     fontsize=23 if n else 26, ha="left",
                     weight="bold" if n == 0 else "normal")
            y -= 0.045
    if footer:
        fig.text(0.5, 0.04, footer, color="#ffd54f", fontsize=24,
                 ha="center", weight="bold")
    fig.savefig(path, dpi=100)


diff = w["Close"].iloc[-1] - w["Close"].iloc[SHOW - 1]
up = diff > 0
side_en = "above resistance" if d == 1 else "below support"
lvl_en = "resistance" if d == 1 else "support"
imp_en = "UP" if a["net"] > 0 else "DOWN"
kind_en = "continuation" if a["cont"] else "reversal"

lines = [
    "PRICE ACTION ANALYSIS",
    f"1) Impulse {imp_en} ${abs(a['net']):.1f} = trend context",
    f"2) Range {CONS} candles, ${h:.1f} wide ({a['top']}T/{a['bot']}B)",
    f"3) Close {side_en}, body {a['ratio']:.1f}x avg",
    (f"4) Retest held: old {lvl_en} flipped" if a["rt"] is not None
     else "4) No retest: strong momentum break"),
    f"5) Type: {kind_en}. Target ${h:.1f}: "
    + ("REACHED" if a["reached"] else "not reached"),
]

sub = f"XAUUSD  |  {tf.upper()}  |  {sess} SESSION"
os.makedirs("out", exist_ok=True)
draw(shown, "out/slide1.png", "UP or DOWN?", "#ffd54f", ylim1, RECT1, sub,
     footer="Mark support/resistance and guess the breakout")
draw(w, "out/slide2.png", "UP ▲" if up else "DOWN ▼",
     "#00e676" if up else "#ff5252", ylim2, RECT2, sub,
     extra=f"${abs(diff):.1f} in {HIDE} candles",
     lines=lines, footer="Post your analysis or your reason in comments",
     analysis=True)

# ---------- متن فارسی ----------
imp_fa = "صعودی" if a["net"] > 0 else "نزولی"
dir_fa = "بالای مقاومت" if d == 1 else "پایین حمایت"
lvl_fa = "مقاومت" if d == 1 else "حمایت"
flip_fa = "حمایت" if d == 1 else "مقاومت"
kind_fa = "ادامه‌ی روند قبلی" if a["cont"] else "برگشت روند (خلاف حرکت قبلی)"
ret_fa = (f"۴) ریتست: قیمت به سطح شکسته‌شده برگشت و نگه داشت؛ {lvl_fa} قبلی تبدیل به {flip_fa} شد و شکست تأیید شد."
          if a["rt"] is not None else
          "۴) بدون ریتست: شکست با مومنتوم قوی انجام شد و قیمت به سطح برنگشت.")
tgt_fa = "به هدف رسید ✅" if a["reached"] else "به هدف نرسید ❌"
news_fa = ("\n\n⏰ این شکست نزدیک ساعت‌های معمول اخبار آمریکا بود؛ نوسان در این ساعت‌ها بیشتره (تقویم خبری واقعی بررسی نشده)."
           if news else "")

caption = (f"طلا (XAUUSD) | تایم‌فریم {STEP[tf]} دقیقه ⏱\n"
           f"سشن: {SESS_FA[sess]} | ساعت شروع رنج: {t_local.strftime('%H:%M')} (وقت تهران)\n"
           "بعد از یه حرکت قوی، قیمت وارد رنج شده 📦\n"
           "شکست به کدوم سمته؟ بالا یا پایین؟ 👆👇\n\n"
           "✍️ حدست رو با دلیل بنویس (حمایت، مقاومت، کندل‌ها)\n"
           "📸 یا عکس تحلیل خودت رو که روی چارت خط‌کشی کردی کامنت کن\n"
           "بعد برو اسلاید دوم و تحلیل کامل رو ببین ✅\n"
           "بهترین تحلیل رو پین می‌کنم 📌\n\n"
           "⚠️ محتوای آموزشی/سرگرمیه و توصیه مالی نیست.\n"
           "#طلا #فارکس #xauusd #gold #پرایس_اکشن #تحلیل_تکنیکال #forex #trading")

analysis_fa = (
    "📊 تحلیل پرایس اکشن (برای کامنت پین‌شده):\n\n"
    f"۱) حرکت قبلی: {imp_fa} قوی به اندازه {abs(a['net']):.1f} دلار؛ این زمینه‌ی روند قبل از رنج بود.\n\n"
    f"۲) رنج: {CONS} کندل با عرض {h:.1f} دلار. مقاومت {a['top']} بار و حمایت {a['bot']} بار تست شد؛ هر چه تست بیشتر، سطح معتبرتر.\n\n"
    f"۳) شکست: کندل {k + 1}ام بعد از رنج {dir_fa} بسته شد و بدنه‌اش {a['ratio']:.1f} برابر میانگین بود. این یعنی {'خریدارها' if d == 1 else 'فروشنده‌ها'} کنترل رو گرفتن. نوع شکست: {kind_fa}.\n\n"
    f"{ret_fa}\n\n"
    f"۵) هدف: ارتفاع رنج ({h:.1f} دلار) از نقطه‌ی شکست؛ قیمت {tgt_fa}"
    f"{news_fa}\n\n"
    "شما چه دلیلی دیده بودید؟ 👇")

open("out/caption.txt", "w", encoding="utf-8").write(caption + "\n-----\n" + analysis_fa)
