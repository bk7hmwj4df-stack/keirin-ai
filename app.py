import streamlit as st
import pandas as pd
import numpy as np
from itertools import permutations

st.set_page_config(page_title="競輪AI v6", page_icon="🚴")

st.title("🚴 競輪AI v6")
st.write("AIが買い目数を自動決定します（最大20点）。")

uploaded = st.file_uploader("📁 競輪CSVをアップロード", type=["csv"])

if uploaded is None:
    st.info("競輪CSVをアップロードしてください。")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"CSV読み込みエラー: {e}")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]

if "rider" not in df.columns or "score" not in df.columns:
    st.error("CSVに rider と score が必要です。")
    st.stop()

df["rider"] = df["rider"].astype(str).str.strip()
df["score"] = pd.to_numeric(df["score"], errors="coerce")
df = df.dropna(subset=["rider", "score"]).copy()

if len(df) < 3:
    st.error("3人以上必要です。")
    st.stop()

for col in ["S", "H", "B", "recent_win_rate"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

st.subheader("📊 選手データ")
st.dataframe(df, use_container_width=True)

# =========================
# AI選手評価
# =========================

def normalize(values):
    values = np.asarray(values, dtype=float)

    lo = values.min()
    hi = values.max()

    if hi == lo:
        return np.ones(len(values)) * 0.5

    return (values - lo) / (hi - lo)


score = normalize(df["score"])

S = normalize(df["S"]) if "S" in df.columns else np.ones(len(df)) * 0.5
H = normalize(df["H"]) if "H" in df.columns else np.ones(len(df)) * 0.5
B = normalize(df["B"]) if "B" in df.columns else np.ones(len(df)) * 0.5

if "recent_win_rate" in df.columns and df["recent_win_rate"].max() > 0:
    recent = normalize(df["recent_win_rate"])
else:
    recent = np.ones(len(df)) * 0.5

ai_score = (
    score * 0.55
    + recent * 0.20
    + S * 0.10
    + H * 0.08
    + B * 0.07
)

# 1着確率
x = ai_score * 5
x = np.exp(x - x.max())
win_prob = x / x.sum()

result = pd.DataFrame({
    "選手": df["rider"],
    "AIスコア": np.round(ai_score, 3),
    "1着確率": np.round(win_prob * 100, 2)
})

result = result.sort_values(
    "1着確率",
    ascending=False
)

st.subheader("🎯 AI 1着確率")
st.dataframe(
    result,
    use_container_width=True,
    hide_index=True
)

# =========================
# 三連単を全通り計算
# =========================

riders = df["rider"].tolist()

prob_map = dict(
    zip(df["rider"], win_prob)
)

tickets = []

for first, second, third in permutations(riders, 3):

    value = (
        prob_map[first] ** 0.60
        * prob_map[second] ** 0.25
        * prob_map[third] ** 0.15
    )

    tickets.append({
        "first": first,
        "second": second,
        "third": third,
        "value": value
    })

tickets.sort(
    key=lambda x: x["value"],
    reverse=True
)

# =========================
# AIが買い目数を自動決定
# =========================

top = tickets[0]["value"]

second = tickets[1]["value"]

ratio = second / top if top > 0 else 0

if ratio < 0.55:
    buy_count = 6
elif ratio < 0.65:
    buy_count = 8
elif ratio < 0.75:
    buy_count = 10
elif ratio < 0.85:
    buy_count = 12
elif ratio < 0.93:
    buy_count = 15
else:
    buy_count = 18

# 絶対に20点を超えない
buy_count = min(buy_count, 20)

selected = tickets[:buy_count]

# =========================
# 最終買い目
# =========================

st.subheader("🔥 AIが決めた最終買い目")

st.success(
    f"AI判断：{buy_count}点"
)

for i, ticket in enumerate(selected, 1):

    st.write(
        f"{i}. "
        f"**{ticket['first']}-"
        f"{ticket['second']}-"
        f"{ticket['third']}**"
    )

# =========================
# フォーメーション
# =========================

st.subheader("🧩 AIフォーメーション")

groups = {}

for ticket in selected:

    first = ticket["first"]

    if first not in groups:
        groups[first] = {}

    second = ticket["second"]

    if second not in groups[first]:
        groups[first][second] = []

    groups[first][second].append(
        ticket["third"]
    )

formation_total = 0

for first, seconds in groups.items():

    for second, thirds in seconds.items():

        thirds = list(
            dict.fromkeys(thirds)
        )

        formation_total += len(thirds)

        third_text = "".join(
            str(x) for x in thirds
        )

        st.write(
            f"**{first}-{second}-{third_text}** "
            f"→ {len(thirds)}点"
        )

st.success(
    f"最終買い目：{buy_count}点"
)

st.caption(
    f"フォーメーション実点数：{formation_total}点"
)

st.info(
    "※AIによる参考予想です。的中を保証するものではありません。"
)
