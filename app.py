import streamlit as st
import pandas as pd
import numpy as np
from itertools import permutations

st.set_page_config(page_title="競輪AI v3", page_icon="🚴")

st.title("🚴 競輪AI v3")
st.write("競輪データをCSVで読み込み、選手評価から三連単12点を予想します。")

uploaded = st.file_uploader(
    "📁 競輪CSVをアップロード",
    type=["csv"]
)

if uploaded is None:
    st.info("まず競輪データのCSVをアップロードしてください。")
    st.write(
        "推奨項目：race_id / rider / score / S / H / B / "
        "recent_win_rate / style / line"
    )
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"CSVを読み込めませんでした: {e}")
    st.stop()

st.subheader("📊 読み込んだデータ")
st.dataframe(df, use_container_width=True)

# 必須項目
required = ["rider", "score"]

missing = [c for c in required if c not in df.columns]

if missing:
    st.error("不足している項目: " + ", ".join(missing))
    st.stop()

# 数値化
for col in ["score", "S", "H", "B", "recent_win_rate"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# 選手番号を文字列にする
df["rider"] = df["rider"].astype(str)

# 7車以上なら先頭7人
df = df.head(7).copy()

if len(df) < 3:
    st.error("3人以上の選手データが必要です。")
    st.stop()

# -------------------------
# 選手評価
# -------------------------

def normalize(series):
    s = series.astype(float)
    if s.max() == s.min():
        return pd.Series([0.5] * len(s), index=s.index)
    return (s - s.min()) / (s.max() - s.min())

df["score_n"] = normalize(df["score"])

if "S" in df.columns:
    df["S_n"] = normalize(df["S"])
else:
    df["S_n"] = 0.5

if "H" in df.columns:
    df["H_n"] = normalize(df["H"])
else:
    df["H_n"] = 0.5

if "B" in df.columns:
    df["B_n"] = normalize(df["B"])
else:
    df["B_n"] = 0.5

if "recent_win_rate" in df.columns:
    wr = df["recent_win_rate"].astype(float)

    # 0.70などの形式にも対応
    if wr.max() <= 1:
        df["win_n"] = wr
    else:
        df["win_n"] = wr / 100
else:
    df["win_n"] = 0.5

# 総合AIスコア
df["ai_score"] = (
    df["score_n"] * 0.45
    + df["S_n"] * 0.15
    + df["H_n"] * 0.15
    + df["B_n"] * 0.10
    + df["win_n"] * 0.15
)

# ライン補正
if "line" in df.columns:
    line_counts = df["line"].astype(str).value_counts()

    df["line_bonus"] = df["line"].astype(str).map(
        lambda x: min(line_counts.get(x, 1) * 0.02, 0.06)
    )

    df["ai_score"] += df["line_bonus"]

# -------------------------
# 1着確率
# -------------------------

# softmax
values = df["ai_score"].to_numpy()

exp_values = np.exp((values - values.max()) * 5)

prob = exp_values / exp_values.sum()

df["win_probability"] = prob * 100

df = df.sort_values(
    "win_probability",
    ascending=False
).reset_index(drop=True)

st.subheader("🎯 AI 1着確率")

show_cols = ["rider", "ai_score", "win_probability"]

st.dataframe(
    df[show_cols].style.format({
        "ai_score": "{:.3f}",
        "win_probability": "{:.2f}%"
    }),
    use_container_width=True
)

# -------------------------
# 三連単210通り
# -------------------------

riders = df["rider"].tolist()

score_map = dict(
    zip(df["rider"], df["ai_score"])
)

prob_map = dict(
    zip(df["rider"], df["win_probability"])
)

# すべての三連単
predictions = []

for a, b, c in permutations(riders, 3):

    # 1着を少し強く評価
    value = (
        score_map[a] * 0.50
        + score_map[b] * 0.30
        + score_map[c] * 0.20
    )

    # 順位差が自然な組み合わせを少し加点
    if prob_map[a] >= prob_map[b]:
        value += 0.02

    if prob_map[b] >= prob_map[c]:
        value += 0.01

    predictions.append({
        "combination": f"{a}-{b}-{c}",
        "value": value
    })

pred = pd.DataFrame(predictions)

# 210通りを順位付け
pred = pred.sort_values(
    "value",
    ascending=False
).reset_index(drop=True)

# 確率として正規化
weights = np.exp((pred["value"] - pred["value"].max()) * 8)

pred["probability"] = (
    weights / weights.sum() * 100
)

st.subheader("🔥 AI三連単ランキング")

for i, row in pred.head(12).iterrows():
    st.write(
        f"**{i+1:02d}. {row['combination']}**"
        f"　{row['probability']:.2f}%"
    )

# -------------------------
# 最終12点
# -------------------------

st.subheader("💰 最終12点")

final_12 = pred.head(12)["combination"].tolist()

for i, bet in enumerate(final_12, 1):
    st.write(f"**{i}. {bet}**")

st.success("予想完了！")

st.caption(
    "※このAIは入力データを統計的に評価する参考予想です。"
    "的中を保証するものではありません。"
)
