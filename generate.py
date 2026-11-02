import yfinance as yf, mplfinance as mpf, pandas as pd, random, os, sys
import numpy as np
import arabic_reshaper
from bidi.algorithm import get_display
import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle

FONT = "fonts/Vazirmatn.ttf"
if os.path.exists(FONT):
    fm.fontManager.addfont(FONT)
    FA_FONT = fm.FontProperties(fname=FONT).get_name()
else:
    FA_FONT = "DejaVu Sans"
matplotlib.rcParams["font.family"] = FA_FONT

PAGE = "@your_page"
DISPLAY_TZ = "Asia/Tehran"
SYMBOLS = ["XAUUSD=X", "GC=F"]
CONFIG = {"1m": dict(period="7d", interval="1m"),
          "5m": dict(period="60d", interval="5m")}
STEP = {"1m": 1, "5m": 5}
IMP, CONS, HIDE = 30, 40, 30
SHOW = IMP + CONS
TOTAL = SHOW + HIDE
SESS_FA = {"ASIA": "آسیا", "LONDON": "لندن",
           "LONDON/NY OVERLAP": "لندن و نیویورک",
           "NEW YORK": "نیویورک"}
GREEN, RED, YELLOW = "#26a69a", "#ef5350", "#ffd54f"
BG = "#0e1117"

reshaper = arabic_reshaper.ArabicReshaper()


def fa(s):
    return get_display(reshaper.reshape(s))


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


def clusters(mask, gap=4):
    n, last = 0, -99
    for i, f in enumerate(mask):
        if f:
            if i - last > gap:
                n += 1
            last = i
    return n


def analyze(w, avg, mult):
    imp, cons, post = w.iloc[:IMP], w.iloc[IMP:SHOW], w.iloc[SHOW:]
    net = imp["Close"].iloc[-1] - imp["Close"].iloc[0]
    rng = imp["High"].max() - imp["Low"].min()
    if rng == 0 or abs(net) < mult * avg:
        return None
    eff = abs(net) / rng
    if eff < 0.5:
        return None
    hi, lo = cons["High"].max(), cons["Low"].min()
    h = hi - lo
    if h < 2.5 * avg or h > 0.7 * abs(net):
        return None
    top = clusters((cons["High"] >= hi - 0.12 * h).values)
    bot = clusters((cons["Low"] <= lo + 0.12 * h).values)
    if top < 2 or bot < 2:
        return None
    cl = post["Close"].values
    out = np.where((cl > hi + 0.15 * h) | (cl < lo - 0.15 * h))[0]
    if len(out) == 0:
        return None
    k = int(out[0])
    if k > 20:
        return None
    d = 1 if cl[k] > hi else -1
    level = hi if d == 1 else lo
    if (cl[-1] - level) * d < 0.5 * h:
        return None
    body = abs(post["Close"].iloc[k] - post["Open"].iloc[k])
    avgb = (cons["Close"] - cons["Open"]).abs().mean()
    ratio = body / avgb if avgb > 0 else 0
    score = top + bot + 4 * eff + min(ratio, 3)
    return dict(net=net, top=top, bot=bot, score=score,
                cont=(d == (1 if net > 0 else -1)))


def pick(df, tf):
    avg = (df["High"] - df["Low"]).mean()
    for mult in (8, 6, 4):
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
            pool = pool[:max(1, len(pool) // 4)]
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

# هر دو اسلاید یک محور قیمت یکسان دارن (بدون سرنخ، ولی چارت بزرگ)
lo2, hi2 = w["Low"].min(), w["High"].max()
pad = (hi2 - lo2) * 0.06
YLIM = (lo2 - pad, hi2 + pad)

RECT = [0.02, 0.17, 0.86, 0.64]
mc = mpf.make_marketcolors(up=GREEN, down=RED, edge="inherit",
                           wick="inherit", inherit=True)
STYLE = mpf.make_mpf_style(marketcolors=mc, facecolor=BG, figcolor=BG,
                           edgecolor="#2a2f3a", gridcolor="#1c212b",
                           gridstyle="-", y_on_right=True,
                           rc={"font.family": FA_FONT})


def tlabels(index, step=10):
    t = pd.DatetimeIndex(index).tz_localize("UTC").tz_convert(DISPLAY_TZ)
    pos = list(range(0, len(t), step))
    return pos, [t[p].strftime("%H:%M") for p in pos]


def draw(data, path, title, tcolor, sub, extra=None, footer=None, result=False):
    # برای اسلاید ۱ هم محور x تا TOTAL کشیده می‌شه (سمت راست خالی)
    fig, axes = mpf.plot(data, type="candle", style=STYLE, ylabel="",
                         returnfig=True, figsize=(10.8, 13.5),
                         datetime_format="%H:%M")
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
        ax.text(SHOW - 1.5, YLIM[1] - (YLIM[1] - YLIM[0]) * 0.02,
                fa("لحظه‌ی حدس"), color="white", fontsize=22,
                ha="right", va="top", weight="bold")

    fig.text(0.5, 0.945, title, color=tcolor, fontsize=56,
             ha="center", va="center", weight="bold")
    fig.text(0.5, 0.895, sub, color="#9aa3b2", fontsize=26,
             ha="center", va="center")
    if extra:
        fig.text(0.5, 0.855, extra, color=tcolor, fontsize=28,
                 ha="center", va="center", weight="bold")
    if footer:
        fig.text(0.5, 0.085, footer, color=YELLOW, fontsize=30,
                 ha="center", va="center", weight="bold")
    fig.text(0.5, 0.04, PAGE, color="#6b7280", fontsize=22,
             ha="center", va="center")
    fig.savefig(path, dpi=100, facecolor=BG)


sub = fa(f"طلا XAUUSD  |  {tf.upper()}  |  سشن {SESS_FA[sess]}")
# نکته: بخش لاتین داخل متن bidi ممکنه جابجا بشه؛ پس خطوط جدا می‌نویسیم
sub = f"XAUUSD   {tf.upper()}   " + fa(f"سشن {SESS_FA[sess]}")

os.makedirs("out", exist_ok=True)
draw(shown, "out/slide1.png", fa("بالا یا پایین؟"), YELLOW, sub,
     footer=fa("خودت تحلیل کن، قیمت از اینجا کجا می‌ره؟"))
draw(w, "out/slide2.png",
     fa("صعودی ▲") if up else fa("نزولی ▼"), col, sub,
     extra=fa(f"قیمت از {p_start:.2f} به {p_end:.2f} رسید"),
     footer=fa("تحلیل یا دلیلت رو کامنت کن"), result=True)

caption = (f"طلا (XAUUSD) | تایم‌فریم {STEP[tf]} دقیقه ⏱\n"
          f"سشن: {SESS_FA[sess]} | ساعت: {t_local.strftime('%H:%M')} (وقت تهران)\n\n"
          "چارت رو خودت تحلیل کن 🧐\n"
          "قیمت از اینجا بالا میره یا پایین؟ 👆👇\n\n"
          "✍️ حدست رو با دلیل بنویس\n"
          "📸 یا عکس تحلیل خودت رو کامنت کن\n"
          "بعد برو اسلاید دوم و جواب رو ببین ✅\n"
          "بهترین تحلیل رو پین می‌کنم 📌\n\n"
          "⚠️ محتوای آموزشی/سرگرمیه و توصیه مالی نیست.\n"
          "#طلا #فارکس #xauusd #gold #پرایس_اکشن #تحلیل_تکنیکال #forex #trading")

dir_fa = "بالا" if up else "پایین"
kind_fa = "ادامه‌ی روند قبلی" if a["cont"] else "برگشت روند"
answer = (f"✅ جواب: قیمت {dir_fa} رفت.\n"
          f"از {p_start:.2f} شروع شد و به {p_end:.2f} رسید.\n\n"
          "نکات برای کامنت پین‌شده:\n"
          f"• قبل از رنج یه حرکت {'صعودی' if a['net'] > 0 else 'نزولی'} قوی بود.\n"
          f"• تو رنج، سقف حدود {a['top']} بار و کف حدود {a['bot']} بار تست شد.\n"
          f"• قیمت از رنج {dir_fa} خارج شد ({kind_fa}).\n\n"
          "شما چی دیده بودید؟ 👇")

open("out/caption.txt", "w", encoding="utf-8").write(caption + "\n-----\n" + answer)
