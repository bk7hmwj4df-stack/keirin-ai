import streamlit as st
import pandas as pd
import numpy as np
from itertools import permutations

st.set_page_config(page_title="競輪AI v5", layout="wide")

st.title("🚴 競輪AI v5")
st.write("競輪CSVを読み込み、選手評価→1着確率→三連単確率→AI自動点数→フォーメーションを作成します。")

uploaded = st.file_uploader(
    "📁 競輪CSVをアップロード",
    type=["csv"]
)

if uploaded is None:
    st.info("まず競輪データのCSVをアップロードしてください。")
    st.write(
        "推奨列：race_id / rider / score / S / H / B / "
        "recent_win_rate / style / line"
    )
    st.stop()

# -----------------------------
# CSV読み込み
# -----------------------------
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"CSVを読み込めませんでした：{e}")
    st.stop()

# 列名を整える
df.columns = [str(c).strip() for c in df.columns]

required = ["race_id", "rider", "score"]

missing = [c for c in required if c not in df.columns]

if missing:
    st.error(
        "必要な列がありません。\n\n"
        + "不足している列："
        + ", ".join(missing)
    )
    st.stop()

# 数値列
numeric_cols = [
    "score",
    "S",
    "H",
    "B",
    "recent_win_rate"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# riderを文字列として保持
df["rider"] = df["rider"].astype(str).str.strip()

st.subheader("📊 読み込んだデータ")
st.dataframe(df, use_container_width=True)

# -----------------------------
# 数値を0～1に正規化
# -----------------------------
def normalize(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)

    mn = series.min()
    mx = series.max()

    if mx == mn:
        return pd.Series(
            np.ones(len(series)) * 0.5,
            index=series.index
        )

    return (series - mn) / (mx - mn)


# -----------------------------
# 1レース予想
# -----------------------------
def predict_race(race):

    race = race.copy().reset_index(drop=True)

    # 選手が3人未満なら予想不能
    if len(race) < 3:
        return None

    # 選手評価
    base = normalize(race["score"])

    if "S" in race.columns:
        s = normalize(race["S"])
    else:
        s = pd.Series(0.5, index=race.index)

    if "H" in race.columns:
        h = normalize(race["H"])
    else:
        h = pd.Series(0.5, index=race.index)

    if "B" in race.columns:
        b = normalize(race["B"])
    else:
        b = pd.Series(0.5, index=race.index)

    if "recent_win_rate" in race.columns:
        recent = normalize(race["recent_win_rate"])
    else:
        recent = pd.Series(0.5, index=race.index)

    # AI総合スコア
    ai_score = (
        base * 0.55
        + recent * 0.20
        + s * 0.10
        + h * 0.08
        + b * 0.07
    )

    race["ai_score"] = ai_score

    # ソフトマックスで1着確率
    x = ai_score.to_numpy(dtype=float)

    temperature = 0.75

    exp_x = np.exp((x - np.max(x)) / temperature)

    probabilities = exp_x / exp_x.sum()

    race["win_probability"] = probabilities

    # AIスコア順
    race = race.sort_values(
        "ai_score",
        ascending=False
    ).reset_index(drop=True)

    # -------------------------
    # 三連単全組み合わせ
    # -------------------------
    riders = race["rider"].tolist()

    prob_map = dict(
        zip(
            race["rider"],
            race["win_probability"]
        )
    )

    # ライン情報
    line_map = {}

    if "line" in race.columns:
        for _, row in race.iterrows():
            line_map[row["rider"]] = str(row["line"])

    tickets = []

    for a, b, c in permutations(riders, 3):

        p = (
            prob_map[a]
            * prob_map[b]
            * prob_map[c]
        )

        # 同ラインの連携を少し評価
        bonus = 1.0

        if line_map.get(a, "") != "":
            if line_map.get(a) == line_map.get(b):
                bonus *= 1.08

            if line_map.get(b) == line_map.get(c):
                bonus *= 1.04

        final_p = p * bonus

        tickets.append(
            {
                "first": a,
                "second": b,
                "third": c,
                "probability": final_p
            }
        )

    tickets = sorted(
        tickets,
        key=lambda x: x["probability"],
        reverse=True
    )

    # -------------------------
    # AIが買い目数を自動決定
    # -------------------------
    top_prob = tickets[0]["probability"]

    if top_prob >= 0.055:
        target = 8
    elif top_prob >= 0.040:
        target = 10
    elif top_prob >= 0.030:
        target = 12
    elif top_prob >= 0.022:
        target = 15
    else:
        target = 18

    # 最大20点
    target = min(target, 20)

    selected = tickets[:target]

    # -------------------------
    # フォーメーション化
    # -------------------------
    # 頭ごとにまとめる
    formation_groups = {}

    for t in selected:
        first = t["first"]

        if first not in formation_groups:
            formation_groups[first] = {
                "seconds": [],
                "thirds": []
            }

        if t["second"] not in formation_groups[first]["seconds"]:
            formation_groups[first]["seconds"].append(
                t["second"]
            )

        if t["third"] not in formation_groups[first]["thirds"]:
            formation_groups[first]["thirds"].append(
                t["third"]
            )

    # 頭の表示順
    first_order = []

    for t in selected:
        if t["first"] not in first_order:
            first_order.append(t["first"])

    formations = []

    for first in first_order:

        group = formation_groups[first]

        seconds = [
            x for x in group["seconds"]
            if x != first
        ]

        thirds = [
            x for x in group["thirds"]
            if x != first
        ]

        if len(seconds) == 0 or len(thirds) == 0:
            continue

        formations.append(
            {
                "first": first,
                "seconds": seconds,
                "thirds": thirds
            }
        )

    return {
        "race": race,
        "tickets": selected,
        "formations": formations,
        "target": target
    }


# -----------------------------
# 全レース予想
# -----------------------------
st.subheader("🎯 AI予想")

race_ids = df["race_id"].dropna().unique()

for race_id in race_ids:

    race = df[df["race_id"] == race_id].copy()

    result = predict_race(race)

    if result is None:
        st.warning(
            f"{race_id}：選手数が少ないため予想できません。"
        )
        continue

    race_result = result["race"]
    selected = result["tickets"]
    formations = result["formations"]

    st.markdown("---")
    st.header(f"🏁 {race_id}")

    # -------------------------
    # 1着確率
    # -------------------------
    st.subheader("🎯 AI 1着確率")

    win_table = race_result[
        [
            "rider",
            "ai_score",
            "win_probability"
        ]
    ].copy()

    win_table["ai_score"] = win_table[
        "ai_score"
    ].round(3)

    win_table["win_probability"] = (
        win_table["win_probability"] * 100
    ).round(2)

    win_table = win_table.rename(
        columns={
            "rider": "選手",
            "ai_score": "AIスコア",
            "win_probability": "1着確率(%)"
        }
    )

    st.dataframe(
        win_table,
        use_container_width=True,
        hide_index=True
    )

    # -------------------------
    # フォーメーション
    # -------------------------
    st.subheader(
        f"🔥 AI自動フォーメーション "
        f"（最大20点・今回は{result['target']}点）"
    )

    for f in formations:

        first = f["first"]
        seconds = "".join(f["seconds"])
        thirds = "".join(f["thirds"])

        st.markdown(
            f"### **{first}-{seconds}-{thirds}**"
        )

    # -------------------------
    # 最終買い目
    # -------------------------
    st.subheader("💰 最終買い目")

    for i, t in enumerate(selected, 1):

        percent = t["probability"] * 100

        st.write(
            f"{i:02d}. "
            f"**{t['first']}-{t['second']}-{t['third']}** "
            f"（{percent:.2f}%）"
        )

    st.success(
        f"予想完了！ AIが自動で{len(selected)}点に絞りました。"
    )

st.markdown("---")

st.caption(
    "※AI予想は入力されたCSVデータを統計的に評価したものです。"
)
