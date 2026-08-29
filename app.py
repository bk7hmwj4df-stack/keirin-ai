import itertools
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="競輪AI v5", page_icon="🚴", layout="wide")

st.title("🚴 競輪AI v5")
st.write("選手評価 → 展開考慮 → 三連単評価 → 自信度に応じて6〜12点 → 自然なフォーメーション化")

uploaded = st.file_uploader("📁 競輪CSVをアップロード", type=["csv"])

if uploaded is None:
    st.info("まず競輪データのCSVをアップロードしてください。")
    st.write("必須列：rider / score")
    st.write("任意列：S / H / B / recent_win_rate / style / line")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"CSVを読み込めませんでした: {e}")
    st.stop()

required = ["rider", "score"]
missing = [c for c in required if c not in df.columns]

if missing:
    st.error("必須列がありません: " + ", ".join(missing))
    st.stop()


# ==============================
# データ整形
# ==============================

for c in ["score", "S", "H", "B", "recent_win_rate"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["rider"] = pd.to_numeric(df["rider"], errors="coerce")
df = df.dropna(subset=["rider"]).copy()
df["rider"] = df["rider"].astype(int)

if len(df) < 3:
    st.error("3人以上の選手データが必要です。")
    st.stop()

if df["rider"].duplicated().any():
    st.error("rider列に重複があります。車番は1人につき1つにしてください。")
    st.stop()


st.subheader("📊 読み込んだデータ")
st.dataframe(df, use_container_width=True)


# ==============================
# Zスコア
# ==============================

def zscore(s):
    std = s.std()

    if pd.isna(std) or std == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)

    return (s - s.mean()) / std


# ==============================
# 選手能力評価
# ==============================

eval_score = zscore(df["score"]).astype(float)

if "S" in df.columns:
    eval_score += zscore(df["S"]) * 0.08

if "H" in df.columns:
    eval_score += zscore(df["H"]) * 0.10

if "B" in df.columns:
    eval_score += zscore(df["B"]) * 0.08

if "recent_win_rate" in df.columns:
    if df["recent_win_rate"].max() > 0:
        eval_score += zscore(df["recent_win_rate"]) * 0.18

df["ai_eval"] = eval_score


# ==============================
# 1着確率
# ==============================

temperature = 1.25

x = eval_score / temperature
p = np.exp(x - x.max())
p = p / p.sum()

riders = df["rider"].tolist()

prob_map = dict(zip(df["rider"], p))
eval_map = dict(zip(df["rider"], eval_score))


prob_df = pd.DataFrame({
    "rider": riders,
    "ai_score": [eval_map[r] for r in riders],
    "win_probability": [prob_map[r] * 100 for r in riders]
})

prob_df = prob_df.sort_values(
    "win_probability",
    ascending=False
).reset_index(drop=True)


st.subheader("🎯 AI 1着確率")

st.dataframe(
    prob_df.style.format({
        "ai_score": "{:.3f}",
        "win_probability": "{:.2f}%"
    }),
    use_container_width=True
)


# ==============================
# 能力値を0〜1に正規化
# ==============================

mn = min(eval_map.values())
mx = max(eval_map.values())

span = mx - mn if mx > mn else 1.0

ability = {
    r: 0.25 + 0.75 * ((eval_map[r] - mn) / span)
    for r in riders
}


# ==============================
# 三連単全通りを評価
#
# 重要：
# 1着だけに極端に偏らない
# ==============================

rows = []

for a, b, c in itertools.permutations(riders, 3):

    first_factor = prob_map[a] ** 0.48

    second_factor = (
        0.55 * ability[b]
        + 0.45 * prob_map[b]
    ) ** 0.31

    third_factor = (
        0.70 * ability[c]
        + 0.30 * prob_map[c]
    ) ** 0.21


    # 2番手・3番手からの逆転も自然に評価
    parity_bonus = 1.0

    if prob_map[b] > prob_map[a] * 0.90:
        parity_bonus *= 1.05

    if prob_map[c] > prob_map[a] * 0.95:
        parity_bonus *= 1.03


    model_score = (
        first_factor
        * second_factor
        * third_factor
        * parity_bonus
    )

    rows.append(
        (
            a,
            b,
            c,
            model_score
        )
    )


tri = pd.DataFrame(
    rows,
    columns=[
        "first",
        "second",
        "third",
        "model_score"
    ]
)


tri["probability"] = (
    tri["model_score"]
    / tri["model_score"].sum()
    * 100
)


tri = tri.sort_values(
    "model_score",
    ascending=False
).reset_index(drop=True)


tri["bet"] = (
    tri["first"].astype(str)
    + "-"
    + tri["second"].astype(str)
    + "-"
    + tri["third"].astype(str)
)


# ==============================
# 自信度から点数決定
#
# 6〜12点
# ==============================

sorted_probs = prob_df["win_probability"].to_numpy()

top1 = sorted_probs[0]

if len(sorted_probs) > 1:
    top2 = sorted_probs[1]
else:
    top2 = 0

gap = top1 - top2


if top1 >= 42 and gap >= 15:
    target_points = 6

elif top1 >= 34 and gap >= 9:
    target_points = 8

elif top1 >= 27 and gap >= 5:
    target_points = 10

else:
    target_points = 12


# ==============================
# 最終買い目選択
#
# 重要：
# 1着固定を優先しない
# 基本的に複数の1着候補を確保
# ==============================

pool_size = min(
    len(tri),
    max(target_points * 5, 40)
)

pool = tri.head(pool_size).copy()


selected_rows = []
selected_set = set()


# 1着候補は基本2人
first_candidates = (
    prob_df["rider"]
    .head(min(3, len(prob_df)))
    .tolist()
)


# ==============================
# まず上位2人を1着に入れる
# ==============================

for r in first_candidates[:2]:

    sub = pool[
        pool["first"] == r
    ]

    if len(sub) > 0:

        row = sub.iloc[0]

        key = (
            int(row["first"]),
            int(row["second"]),
            int(row["third"])
        )

        if key not in selected_set:

            selected_rows.append(row)
            selected_set.add(key)


# ==============================
# 残りを総合評価順に追加
# ==============================

for _, row in pool.iterrows():

    key = (
        int(row["first"]),
        int(row["second"]),
        int(row["third"])
    )

    if key in selected_set:
        continue

    selected_rows.append(row)
    selected_set.add(key)

    if len(selected_rows) >= target_points:
        break


# ==============================
# 点数不足時
# ==============================

if len(selected_rows) < target_points:

    for _, row in tri.iterrows():

        key = (
            int(row["first"]),
            int(row["second"]),
            int(row["third"])
        )

        if key not in selected_set:

            selected_rows.append(row)
            selected_set.add(key)

        if len(selected_rows) >= target_points:
            break


selected_df = pd.DataFrame(
    selected_rows
)

selected_df = selected_df.sort_values(
    "model_score",
    ascending=False
).reset_index(drop=True)


# ==============================
# AI三連単ランキング
# ==============================

st.subheader("🔥 AI三連単ランキング")

for i, r in tri.head(12).iterrows():

    st.write(
        f"**{i + 1:02d}. {r['bet']}**　"
        f"{r['probability']:.2f}%"
    )


# ==============================
# 最終買い目
# ==============================

st.subheader(
    f"💰 最終{target_points}点"
)

for i, r in selected_df.iterrows():

    st.write(
        f"{i + 1}. **{r['bet']}**"
    )


# ==============================
# フォーメーション化
#
# 選んだ買い目と完全一致する形だけ
# 採用する
#
# 余計な買い目を増やさない
# ==============================

selected = {

    (
        int(r["first"]),
        int(r["second"]),
        int(r["third"])
    )

    for _, r in selected_df.iterrows()
}


def valid_rect(
    a_set,
    b_set,
    c_set,
    remaining
):

    combos = {

        (a, b, c)

        for a in a_set
        for b in b_set
        for c in c_set

        if len({a, b, c}) == 3
    }

    if not combos:
        return None

    if combos.issubset(remaining):
        return combos

    return None


def set_label(values):

    return "".join(
        str(x)
        for x in sorted(values)
    )


def search_best_rectangle(remaining):

    first_values = sorted(
        {x[0] for x in remaining}
    )

    second_values = sorted(
        {x[1] for x in remaining}
    )

    third_values = sorted(
        {x[2] for x in remaining}
    )


    best = None
    best_key = None


    # 1着複数を優先
    for ka in range(
        1,
        min(3, len(first_values)) + 1
    ):

        for aset in itertools.combinations(
            first_values,
            ka
        ):

            for kb in range(
                1,
                min(3, len(second_values)) + 1
            ):

                for bset in itertools.combinations(
                    second_values,
                    kb
                ):

                    for kc in range(
                        1,
                        min(4, len(third_values)) + 1
                    ):

                        for cset in itertools.combinations(
                            third_values,
                            kc
                        ):

                            rect = valid_rect(
                                aset,
                                bset,
                                cset,
                                remaining
                            )

                            if rect is None:
                                continue

                            size = len(rect)

                            if size < 2:
                                continue


                            # 1着複数を優先
                            multi_first_bonus = (
                                2
                                if len(aset) >= 2
                                else 0
                            )

                            multi_second_bonus = (
                                1
                                if len(bset) >= 2
                                else 0
                            )

                            compact_penalty = (
                                len(aset)
                                + len(bset)
                                + len(cset)
                            )


                            key = (

                                size,

                                multi_first_bonus,

                                multi_second_bonus,

                                -compact_penalty
                            )


                            if (
                                best_key is None
                                or key > best_key
                            ):

                                best_key = key

                                best = (
                                    tuple(aset),
                                    tuple(bset),
                                    tuple(cset),
                                    rect
                                )


    return best


# ==============================
# 選んだ買い目を
# フォーメーションに変換
# ==============================

remaining = set(selected)

formations = []


while remaining:

    best = search_best_rectangle(
        remaining
    )


    # フォーメーション化できない場合
    if best is None:

        x = max(

            remaining,

            key=lambda t: float(

                selected_df[

                    (
                        selected_df["first"] == t[0]
                    )

                    &

                    (
                        selected_df["second"] == t[1]
                    )

                    &

                    (
                        selected_df["third"] == t[2]
                    )

                ]["model_score"].iloc[0]

            )

        )


        formations.append(

            (
                "single",

                (x[0],),

                (x[1],),

                (x[2],),

                {x}

            )

        )

        remaining.remove(x)


    else:

        aset, bset, cset, rect = best

        formations.append(

            (
                "rect",

                aset,

                bset,

                cset,

                rect

            )

        )

        remaining -= rect


# ==============================
# 最終フォーメーション表示
# ==============================

st.subheader(
    "🧩 最終フォーメーション"
)


total_points = 0


for (
    kind,
    aset,
    bset,
    cset,
    rect
) in formations:


    label = (
        f"{set_label(aset)}-"
        f"{set_label(bset)}-"
        f"{set_label(cset)}"
    )


    count = len(rect)

    total_points += count


    st.write(
        f"**{label}**　→ {count}点"
    )


st.caption(
    f"フォーメーション合計："
    f"{total_points}点"
    f"（最終{target_points}点と一致）"
)


# ==============================
# 最終結論
# ==============================

st.success("予想完了！")


firsts = sorted(
    selected_df["first"]
    .unique()
    .tolist()
)


seconds = sorted(
    selected_df["second"]
    .unique()
    .tolist()
)


thirds = sorted(
    selected_df["third"]
    .unique()
    .tolist()
)


st.subheader("🏁 最終結論")


st.write(

    f"**"

    f"1着候補："
    f"{''.join(map(str, firsts))}　"

    f"2着候補："
    f"{''.join(map(str, seconds))}　"

    f"3着候補："
    f"{''.join(map(str, thirds))}"

    f"**"

)


st.info(

    "AIは入力データを統計的に評価した参考予想です。"

    "的中を保証するものではありません。"

)
