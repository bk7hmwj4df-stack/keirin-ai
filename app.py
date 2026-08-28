import streamlit as st
import pandas as pd
import numpy as np
from itertools import permutations

st.set_page_config(page_title="競輪AI v2", page_icon="🚴")

st.title("🚴 競輪AI v2")
st.write("競輪データをCSVで読み込んで、1着確率と三連単12点を予想します。")

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

if "rider" not in df.columns:
    st.error("CSVに「rider」列が必要です。")
    st.stop()

# 数値化できる列
numeric_cols = [
    "score", "S", "H", "B",
    "recent_win_rate", "win_rate",
    "recent", "strength"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# 総合評価
def make_score(row):
    score = 0.0

    if "score" in df.columns:
        score += float(row.get("score", 0)) * 1.0

    if "S" in df.columns:
        score += float(row.get("S", 0)) * 2.0

    if "H" in df.columns:
        score += float(row.get("H", 0)) * 1.5

    if "B" in df.columns:
        score += float(row.get("B", 0)) * 1.5

    if "recent_win_rate" in df.columns:
        score += float(row.get("recent_win_rate", 0)) * 20

    if "win_rate" in df.columns:
        score += float(row.get("win_rate", 0)) * 20

    if "recent" in df.columns:
        score += float(row.get("recent", 0))

    if "strength" in df.columns:
        score += float(row.get("strength", 0))

    return score

df["AI_score"] = df.apply(make_score, axis=1)

# 同じレースだけを選択
if "race_id" in df.columns:
    races = df["race_id"].dropna().astype(str).unique()

    if len(races) > 1:
        race_id = st.selectbox("🏁 レースを選択", races)
        race = df[df["race_id"].astype(str) == race_id].copy()
    else:
        race = df.copy()
else:
    race = df.copy()

race = race.reset_index(drop=True)

if len(race) < 3:
    st.error("3人以上の選手データが必要です。")
    st.stop()

# AI確率
values = race["AI_score"].astype(float).values

# 数値が全部同じ場合にも対応
if np.max(values) == np.min(values):
    probs = np.ones(len(values)) / len(values)
else:
    x = values - np.max(values)
    exp_x = np.exp(x)
    probs = exp_x / exp_x.sum()

race["1着確率"] = probs * 100
race = race.sort_values("1着確率", ascending=False).reset_index(drop=True)

st.subheader("🎯 AI 1着確率")

show_cols = ["rider", "AI_score", "1着確率"]

if "line" in race.columns:
    show_cols.append("line")

st.dataframe(
    race[show_cols].style.format({"1着確率": "{:.1f}%"}),
    use_container_width=True
)

# 三連単210通り
riders = race["rider"].astype(str).tolist()

prob_map = dict(zip(
    riders,
    race["1着確率"].astype(float)
))

combos = []

for a, b, c in permutations(riders, 3):
    p = (
        prob_map[a] / 100
        * prob_map[b] / 100
        * prob_map[c] / 100
    )

    combos.append({
        "買い目": f"{a}-{b}-{c}",
        "期待確率": p
    })

combos = sorted(
    combos,
    key=lambda x: x["期待確率"],
    reverse=True
)

st.subheader("🔥 AI三連単ランキング")

for i, item in enumerate(combos[:12], 1):
    st.write(
        f"**{i:02d}. {item['買い目']}**　"
        f"{item['期待確率'] * 100:.2f}%"
    )

st.subheader("💰 最終12点")

final = [x["買い目"] for x in combos[:12]]

st.code("\n".join(final))

st.success("予想完了！")
st.caption("※これは統計的な参考予想で、的中を保証するものではありません。")
