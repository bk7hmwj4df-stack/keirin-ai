import streamlit as st
import pandas as pd
import numpy as np
from itertools import permutations

st.set_page_config(page_title="競輪AI v6", page_icon="🚴")

st.title("🚴 競輪AI v6")
st.write("従来の予想ロジックを維持し、買い目数だけAIが6〜20点で自動調整します。")

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

for col in ["S", "H", "B", "recent_win_rate"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

if len(df) < 3:
    st.error("3人以上の選手が必要です。")
    st.stop()

st.subheader("📊 読み込んだデータ")
st.dataframe(df, use_container_width=True)

def normalize(series):
    x = pd.to_numeric(series, errors="coerce").fillna(0)
    lo = x.min()
    hi = x.max()

    if hi == lo:
        return np.ones(len(x)) * 0.5

    return ((x - lo) / (hi - lo)).to_numpy()

score_n = normalize(df["score"])

if "S" in df.columns:
    S_n = normalize(df["S"])
else:
    S_n = np.ones(len(df)) * 0.5

if "H" in df.columns:
    H_n = normalize(df["H"])
else:
    H_n = np.ones(len(df)) * 0.5

if "B" in df.columns:
    B_n = normalize(df["B"])
else:
    B_n = np.ones(len(df)) * 0.5

if "recent_win_rate" in df.columns and df["recent_win_rate"].max() > 0:
    recent_n = normalize(df["recent_win_rate"])
else:
    recent_n = np.ones(len(df)) * 0.5

ai_score = (
    score_n * 0.55
    + recent_n * 0.20
    + S_n * 0.10
    + H_n * 0.08
    + B_n * 0.07
)

x = ai_score / 1.15
exp_x = np.exp(x - x.max())
win_probability = exp_x / exp_x.sum()

result = pd.DataFrame({
    "選手": df["rider"],
    "AIスコア": np.round(ai_score, 3),
    "1着確率": np.round(win_probability * 100, 2)
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

riders = df["rider"].tolist()

prob_map = dict(
    zip(df["rider"], win_probability)
)

base = dict(
    zip(df["rider"], ai_score)
)

mn = min(base.values())
mx = max(base.values())
span = mx - mn if mx > mn else 1

ability = {}

for rider, value in base.items():
    ability[rider] = (
        0.55
        + 0.45 * ((value - mn) / span)
    )

tickets = []

for first, second, third in permutations(riders, 3):

    model_score = (
        prob_map[first] ** 0.62
        * ability[second] ** 0.23
        * ability[third] ** 0.15
    )

    tickets.append({
        "first": first,
        "second": second,
        "third": third,
        "score": model_score
    })

tickets.sort(
    key=lambda x: x["score"],
    reverse=True
)

total_score = sum(
    ticket["score"]
    for ticket in tickets
)

for ticket in tickets:
    ticket["probability"] = (
        ticket["score"]
        / total_score
        * 100
    )

st.subheader("🔥 AI三連単ランキング")

for i, ticket in enumerate(tickets[:12], 1):

    st.write(
        f"**{i:02d}. "
        f"{ticket['first']}-"
        f"{ticket['second']}-"
        f"{ticket['third']}** "
        f"{ticket['probability']:.2f}%"
    )

# AIが点数だけ自動決定
relative = (
    np.array([x["score"] for x in tickets[:20]])
    / tickets[0]["score"]
)

buy_count = int(
    np.sum(relative >= 0.52)
)

buy_count = max(
    6,
    min(20, buy_count)
)

selected = tickets[:buy_count]

st.subheader("💰 AIが決めた最終買い目")

st.success(
    f"AI判断：{buy_count}点"
)

for i, ticket in enumerate(selected, 1):

    st.write(
        f"{i}. **"
        f"{ticket['first']}-"
        f"{ticket['second']}-"
        f"{ticket['third']}**"
    )

st.subheader("🧩 AIフォーメーション")

groups = {}

for ticket in selected:

    first = ticket["first"]
    second = ticket["second"]
    third = ticket["third"]

    if first not in groups:
        groups[first] = {}

    if second not in groups[first]:
        groups[first][second] = []

    groups[first][second].append(third)

for first in groups:

    for second in groups[first]:

        thirds = groups[first][second]

        third_text = "".join(
            str(x)
            for x in thirds
        )

        st.write(
            f"**{first}-{second}-{third_text}** "
            f"→ {len(thirds)}点"
        )

st.success(
    f"最終買い目：{buy_count}点"
)

st.info(
    "予想ロジックは従来版を維持しています。"
    "AIが点数だけ6〜20点の範囲で自動調整します。"
    "※的中を保証するものではありません。"
)
