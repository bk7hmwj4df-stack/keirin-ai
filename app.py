import itertools
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="競輪AI v4", page_icon="🚴", layout="wide")

st.title("🚴 競輪AI v4")
st.write("競輪CSVを読み込み、選手評価→1着確率→三連単210通り→最終12点をフォーメーション化します。")

uploaded = st.file_uploader(
    "📁 競輪CSVをアップロード",
    type=["csv"]
)

if uploaded is None:
    st.info("まず競輪データのCSVをアップロードしてください。")
    st.write("推奨列：race_id / rider / score / S / H / B / recent_win_rate / style / line")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"CSVを読み込めませんでした: {e}")
    st.stop()

st.subheader("📊 読み込んだデータ")
st.dataframe(df, use_container_width=True)

required = ["rider", "score"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error("必須列がありません: " + ", ".join(missing))
    st.stop()

# 数値列を安全に変換
for c in ["score", "S", "H", "B", "recent_win_rate"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["rider"] = pd.to_numeric(df["rider"], errors="coerce")
df = df.dropna(subset=["rider"]).copy()
df["rider"] = df["rider"].astype(int)

if len(df) < 3:
    st.error("3人以上の選手データが必要です。")
    st.stop()

# ---------- 選手評価 ----------
# 欠損項目があっても動くよう、存在する情報だけを利用
score = df["score"].astype(float)
score_z = (score - score.mean()) / (score.std() if score.std() > 0 else 1)

eval_score = score_z.copy()

if "S" in df.columns:
    eval_score += (df["S"] - df["S"].mean()) / (df["S"].std() if df["S"].std() > 0 else 1) * 0.10
if "H" in df.columns:
    eval_score += (df["H"] - df["H"].mean()) / (df["H"].std() if df["H"].std() > 0 else 1) * 0.12
if "B" in df.columns:
    eval_score += (df["B"] - df["B"].mean()) / (df["B"].std() if df["B"].std() > 0 else 1) * 0.10
if "recent_win_rate" in df.columns and df["recent_win_rate"].max() > 0:
    rw = df["recent_win_rate"]
    eval_score += (rw - rw.mean()) / (rw.std() if rw.std() > 0 else 1) * 0.18

# softmaxで1着確率
temperature = 1.15
x = eval_score / temperature
p = np.exp(x - x.max())
p = p / p.sum()

prob_df = pd.DataFrame({
    "rider": df["rider"],
    "ai_score": eval_score.round(3),
    "win_probability": (p * 100).round(2)
}).sort_values("win_probability", ascending=False)

st.subheader("🎯 AI 1着確率")
st.dataframe(prob_df, use_container_width=True)

# ---------- 三連単210通り ----------
riders = df["rider"].tolist()
prob_map = dict(zip(df["rider"], p))

# 2着・3着は1着確率だけでなく、能力差を少し反映したスコア
base = {int(r): float(s) for r, s in zip(df["rider"], eval_score)}
mn, mx = min(base.values()), max(base.values())
span = mx - mn if mx > mn else 1
ability = {r: 0.55 + 0.45 * ((v - mn) / span) for r, v in base.items()}

rows = []
for a, b, c in itertools.permutations(riders, 3):
    # 1着確率を強め、2・3着の能力も加味
    score3 = (
        prob_map[a] ** 0.62
        * ability[b] ** 0.23
        * ability[c] ** 0.15
    )
    rows.append((f"{a}-{b}-{c}", a, b, c, score3))

tri = pd.DataFrame(rows, columns=["bet", "first", "second", "third", "model_score"])
tri = tri.sort_values("model_score", ascending=False).reset_index(drop=True)

# 正規化した相対確率表示
tri["probability"] = tri["model_score"] / tri["model_score"].sum() * 100

st.subheader("🔥 AI三連単ランキング")
for i, r in tri.head(12).iterrows():
    st.write(f"**{i+1:02d}. {r['bet']}**  {r['probability']:.2f}%")

# ---------- 最終12点 ----------
top = tri.head(12).copy()
top_bets = top["bet"].tolist()

st.subheader("💰 最終12点")
for i, bet in enumerate(top_bets, 1):
    st.write(f"{i}. **{bet}**")

# ---------- フォーメーション化 ----------
# 選ばれた12点だけを集合として扱い、余計な買い目を発生させない。
selected = set((int(r["first"]), int(r["second"]), int(r["third"])) for _, r in top.iterrows())

def contained_rectangle(a_set, b_set, c_set):
    combos = {(a, b, c) for a in a_set for b in b_set for c in c_set
              if len({a, b, c}) == 3}
    return combos and combos.issubset(selected)

def rectangle_key(rect):
    a, b, c = rect
    return (
        tuple(sorted(a)),
        tuple(sorted(b)),
        tuple(sorted(c))
    )

# まず「同じ1着×複数2着×複数3着」の自然なまとまりを探す。
# 必ず選択済み12点の中だけに収まる組み合わせを採用。
remaining = set(selected)
formations = []

while remaining:
    best = None
    best_gain = 0

    # 最大4×4程度の小さな集合を探索
    for first in sorted({x[0] for x in remaining}):
        seconds = sorted({x[1] for x in remaining if x[0] == first})
        for second in seconds:
            thirds = sorted({x[2] for x in remaining if x[0] == first and x[1] == second})
            # 1着固定・2着複数・3着複数
            for k2 in range(min(3, len(seconds)), 0, -1):
                for bset in itertools.combinations(seconds, k2):
                    for k3 in range(min(4, len(thirds)), 0, -1):
                        for cset in itertools.combinations(thirds, k3):
                            rect = {(first, b, c) for b in bset for c in cset
                                    if len({first, b, c}) == 3}
                            if rect and rect.issubset(remaining):
                                gain = len(rect)
                                if gain > best_gain:
                                    best_gain = gain
                                    best = (first, tuple(bset), tuple(cset), rect)

    # 次に「1着複数×2着固定×3着固定」のまとまり
    if best is None:
        for second in sorted({x[1] for x in remaining}):
            firsts = sorted({x[0] for x in remaining if x[1] == second})
            thirds = sorted({x[2] for x in remaining if x[1] == second})
            for k1 in range(min(3, len(firsts)), 0, -1):
                for aset in itertools.combinations(firsts, k1):
                    for k3 in range(min(3, len(thirds)), 0, -1):
                        for cset in itertools.combinations(thirds, k3):
                            rect = {(a, second, c) for a in aset for c in cset
                                    if len({a, second, c}) == 3}
                            if rect and rect.issubset(remaining) and len(rect) > best_gain:
                                best_gain = len(rect)
                                best = (tuple(aset), second, tuple(cset), rect)

    if best is None:
        x = next(iter(remaining))
        formations.append(("single", x))
        remaining.remove(x)
    else:
        formations.append(("rect", best))
        remaining -= best[3]

def nums(v):
    if isinstance(v, tuple):
        return "".join(str(x) for x in sorted(v))
    return str(v)

st.subheader("🧩 最終12点をフォーメーション表示")

formation_points = []
for item in formations:
    if item[0] == "single":
        bet = "-".join(map(str, item[1]))
        formation_points.append((bet, 1))
    else:
        _, a, b, c, rect = item
        # a/b/cがスカラーまたはtuple
        aa = nums(a)
        bb = nums(b)
        cc = nums(c)
        formation_points.append((f"{aa}-{bb}-{cc}", len(rect)))

for bet, count in formation_points:
    st.write(f"**{bet}**　→ {count}点")

st.caption(f"フォーメーション合計：{sum(x[1] for x in formation_points)}点（最終12点と一致）")
st.success("予想完了！")
st.info("AIは入力データを統計的に評価した参考予想です。的中を保証するものではありません。")
