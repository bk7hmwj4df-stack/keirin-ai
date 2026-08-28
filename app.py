import itertools
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="競輪AI v5",
    page_icon="🚴",
    layout="wide"
)

st.title("🚴 競輪AI v5")
st.write(
    "競輪CSVを読み込み、選手評価→1着確率→三連単候補→"
    "レース自信度に応じて6〜12点を自動選択します。"
)

# =========================================================
# CSV読み込み
# =========================================================

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

# =========================================================
# データ整形
# =========================================================

for c in [
    "score",
    "S",
    "H",
    "B",
    "recent_win_rate"
]:
    if c in df.columns:
        df[c] = pd.to_numeric(
            df[c],
            errors="coerce"
        ).fillna(0)

df["rider"] = pd.to_numeric(
    df["rider"],
    errors="coerce"
)

df = df.dropna(
    subset=["rider"]
).copy()

df["rider"] = df["rider"].astype(int)

if "race_id" not in df.columns:
    df["race_id"] = "race1"

if "style" not in df.columns:
    df["style"] = "両"

if "line" not in df.columns:
    df["line"] = ""

if "recent_win_rate" not in df.columns:
    df["recent_win_rate"] = 0

if len(df) < 3:
    st.error("3人以上の選手データが必要です。")
    st.stop()

# =========================================================
# 選手評価
# =========================================================

score = df["score"].astype(float)

score_std = (
    score.std()
    if score.std() > 0
    else 1
)

eval_score = (
    (score - score.mean())
    / score_std
)

# S
if "S" in df.columns:

    s_std = (
        df["S"].std()
        if df["S"].std() > 0
        else 1
    )

    eval_score += (
        (df["S"] - df["S"].mean())
        / s_std
    ) * 0.10

# H
if "H" in df.columns:

    h_std = (
        df["H"].std()
        if df["H"].std() > 0
        else 1
    )

    eval_score += (
        (df["H"] - df["H"].mean())
        / h_std
    ) * 0.12

# B
if "B" in df.columns:

    b_std = (
        df["B"].std()
        if df["B"].std() > 0
        else 1
    )

    eval_score += (
        (df["B"] - df["B"].mean())
        / b_std
    ) * 0.10

# 最近勝率
rw = df["recent_win_rate"]

if rw.max() > 0:

    rw_std = (
        rw.std()
        if rw.std() > 0
        else 1
    )

    eval_score += (
        (rw - rw.mean())
        / rw_std
    ) * 0.18

# 脚質
style_num = (
    df["style"]
    .astype(str)
    .map({
        "逃": 3,
        "先": 3,
        "両": 2,
        "捲": 2,
        "追": 1
    })
    .fillna(2)
)

eval_score += (
    style_num - style_num.mean()
) * 0.08

# =========================================================
# ライン評価
# =========================================================

df["line_size"] = (
    df.groupby(
        ["race_id", "line"]
    )["rider"]
    .transform("count")
)

df["line_score"] = (
    df.groupby(
        ["race_id", "line"]
    )["score"]
    .transform("sum")
)

line_mean = df["line_score"].mean()

line_std = (
    df["line_score"].std()
    if df["line_score"].std() > 0
    else 1
)

eval_score += (
    (df["line_score"] - line_mean)
    / line_std
) * 0.08

# =========================================================
# 1着確率
# =========================================================

temperature = 1.15

x = eval_score / temperature

p = np.exp(
    x - x.max()
)

p = p / p.sum()

prob_df = pd.DataFrame({
    "rider": df["rider"],
    "ai_score": eval_score.round(3),
    "win_probability": (
        p * 100
    ).round(2)
})

prob_df = prob_df.sort_values(
    "win_probability",
    ascending=False
)

st.subheader("🎯 AI 1着確率")

st.dataframe(
    prob_df,
    use_container_width=True
)

# =========================================================
# ライン補正
# =========================================================

riders = [
    int(x)
    for x in df["rider"].tolist()
]

prob_map = dict(
    zip(
        df["rider"],
        p
    )
)

base = {
    int(r): float(s)
    for r, s in zip(
        df["rider"],
        eval_score
    )
}

mn = min(base.values())
mx = max(base.values())

span = (
    mx - mn
    if mx > mn
    else 1
)

ability = {
    r: 0.55 + 0.45 * (
        (v - mn) / span
    )
    for r, v in base.items()
}

line_bonus = {
    r: 1.0
    for r in riders
}

for _, group in df.groupby(
    ["race_id", "line"]
):

    members = [
        int(x)
        for x in group["rider"].tolist()
    ]

    if len(members) >= 2:

        bonus = 1.0 + min(
            0.05,
            0.015 * (
                len(members) - 1
            )
        )

        for r in members:
            line_bonus[r] = bonus

# =========================================================
# 三連単210通り
# =========================================================

rows = []

for a, b, c in itertools.permutations(
    riders,
    3
):

    model_score = (
        prob_map[a] ** 0.62
        * ability[b] ** 0.23
        * ability[c] ** 0.15
        * line_bonus[a]
        * line_bonus[b] ** 0.5
    )

    rows.append([
        f"{a}-{b}-{c}",
        a,
        b,
        c,
        model_score
    ])

tri = pd.DataFrame(
    rows,
    columns=[
        "bet",
        "first",
        "second",
        "third",
        "model_score"
    ]
)

tri = tri.sort_values(
    "model_score",
    ascending=False
).reset_index(
    drop=True
)

tri["probability"] = (
    tri["model_score"]
    / tri["model_score"].sum()
    * 100
)

# =========================================================
# レース自信度
# =========================================================

p_sorted = np.sort(
    p
)[::-1]

top1 = float(
    p_sorted[0]
)

top2 = float(
    p_sorted[:2].sum()
)

gap = float(
    p_sorted[0]
    - p_sorted[1]
)

confidence_score = (
    top1 * 45
    + top2 * 30
    + min(
        gap * 100,
        25
    )
)

# 7車立てなどは少しだけ厳しく
if len(riders) >= 7:
    confidence_score -= 3

confidence_score = float(
    np.clip(
        confidence_score,
        0,
        100
    )
)

# =========================================================
# 自信度 → 点数
# =========================================================

if confidence_score >= 46:

    confidence_label = "★★★"
    target_n = 7

elif confidence_score >= 38:

    confidence_label = "★★☆"
    target_n = 9

elif confidence_score >= 31:

    confidence_label = "★☆☆"
    target_n = 11

else:

    confidence_label = "★☆☆"
    target_n = 12

# 境界を少し変化させる
if 44 <= confidence_score < 46:
    target_n = 8

elif 36 <= confidence_score < 38:
    target_n = 10

# =========================================================
# AI三連単ランキング
# =========================================================

st.subheader("🔥 AI三連単ランキング")

for i, row in tri.head(12).iterrows():

    st.write(
        f"**{i + 1:02d}. {row['bet']}** "
        f"{row['probability']:.2f}%"
    )

# =========================================================
# 最終買い目選択
# =========================================================

candidates = []

first_count = {}
second_count = {}

for i in tri.index:

    row = tri.loc[i]

    first = int(
        row["first"]
    )

    second = int(
        row["second"]
    )

    penalty = (
        1
        + 0.18
        * first_count.get(
            first,
            0
        )
        + 0.16
        * second_count.get(
            second,
            0
        )
    )

    adjusted_score = (
        float(row["model_score"])
        / penalty
    )

    candidates.append([
        adjusted_score,
        i
    ])

candidates.sort(
    reverse=True
)

chosen = []

first_count = {}
second_count = {}

for adjusted_score, i in candidates:

    row = tri.loc[i]

    first = int(
        row["first"]
    )

    second = int(
        row["second"]
    )

    # 2着が偏りすぎる場合は飛ばす
    if second_count.get(
        second,
        0
    ) >= max(
        3,
        int(
            np.ceil(
                target_n / 3
            )
        )
    ):
        continue

    chosen.append(i)

    first_count[first] = (
        first_count.get(
            first,
            0
        ) + 1
    )

    second_count[second] = (
        second_count.get(
            second,
            0
        ) + 1
    )

    if len(chosen) >= target_n:
        break

# 足りなければランキングから補充
if len(chosen) < target_n:

    for i in tri.index:

        if i not in chosen:

            chosen.append(i)

        if len(chosen) >= target_n:
            break

top = tri.loc[
    chosen
].copy()

# =========================================================
# 自信度表示
# =========================================================

st.subheader("🧠 レース自信度")

st.write(
    f"**{confidence_label}　"
    f"{confidence_score:.1f}/100　"
    f"→ 最終{target_n}点**"
)

# =========================================================
# 最終買い目
# =========================================================

st.subheader(
    f"💰 最終{target_n}点"
)

for i, (_, row) in enumerate(
    top.iterrows(),
    1
):

    st.write(
        f"{i}. **{row['bet']}**"
    )

# =========================================================
# フォーメーション化
# =========================================================

selected = set()

for _, row in top.iterrows():

    selected.add(
        (
            int(row["first"]),
            int(row["second"]),
            int(row["third"])
        )
    )

remaining = set(
    selected
)

formations = []

while remaining:

    best = None
    best_gain = 0

    # -----------------------------------------------------
    # 1着固定 × 2着複数 × 3着複数
    # -----------------------------------------------------

    first_values = sorted(
        set(
            x[0]
            for x in remaining
        )
    )

    for first in first_values:

        seconds = sorted(
            set(
                x[1]
                for x in remaining
                if x[0] == first
            )
        )

        for k2 in range(
            min(3, len(seconds)),
            0,
            -1
        ):

            for second_set in itertools.combinations(
                seconds,
                k2
            ):

                thirds = sorted(
                    set(
                        x[2]
                        for x in remaining
                        if (
                            x[0] == first
                            and x[1]
                            in second_set
                        )
                    )
                )

                for k3 in range(
                    min(4, len(thirds)),
                    0,
                    -1
                ):

                    for third_set in itertools.combinations(
                        thirds,
                        k3
                    ):

                        rect = set()

                        for second in second_set:

                            for third in third_set:

                                if len({
                                    first,
                                    second,
                                    third
                                }) == 3:

                                    rect.add(
                                        (
                                            first,
                                            second,
                                            third
                                        )
                                    )

                        if (
                            rect
                            and rect.issubset(
                                remaining
                            )
                            and len(rect)
                            > best_gain
                        ):

                            best_gain = len(
                                rect
                            )

                            best = (
                                first,
                                tuple(
                                    second_set
                                ),
                                tuple(
                                    third_set
                                ),
                                rect
                            )

    # -----------------------------------------------------
    # 1着複数 × 2着固定 × 3着複数
    # -----------------------------------------------------

    if best is None:

        second_values = sorted(
            set(
                x[1]
                for x in remaining
            )
        )

        for second in second_values:

            firsts = sorted(
                set(
                    x[0]
                    for x in remaining
                    if x[1] == second
                )
            )

            thirds = sorted(
                set(
                    x[2]
                    for x in remaining
                    if x[1] == second
                )
            )

            for k1 in range(
                min(3, len(firsts)),
                0,
                -1
            ):

                for first_set in itertools.combinations(
                    firsts,
                    k1
                ):

                    for k3 in range(
                        min(3, len(thirds)),
                        0,
                        -1
                    ):

                        for third_set in itertools.combinations(
                            thirds,
                            k3
                        ):

                            rect = set()

                            for first in first_set:

                                for third in third_set:

                                    if len({
                                        first,
                                        second,
                                        third
                                    }) == 3:

                                        rect.add(
                                            (
                                                first,
                                                second,
                                                third
                                            )
                                        )

                            if (
                                rect
                                and rect.issubset(
                                    remaining
                                )
                                and len(rect)
                                > best_gain
                            ):

                                best_gain = len(
                                    rect
                                )

                                best = (
                                    tuple(
                                        first_set
                                    ),
                                    second,
                                    tuple(
                                        third_set
                                    ),
                                    rect
                                )

    # -----------------------------------------------------
    # 見つからなければ単独買い目
    # -----------------------------------------------------

    if best is None:

        single = next(
            iter(remaining)
        )

        formations.append(
            (
                "single",
                single
            )
        )

        remaining.remove(
            single
        )

    else:

        formations.append(
            (
                "rect",
                best
            )
        )

        remaining -= best[3]

# =========================================================
# 安全な文字列変換
# =========================================================

def nums(value):

    if isinstance(
        value,
        tuple
    ):

        return "".join(
            str(x)
            for x in sorted(value)
        )

    return str(value)

# =========================================================
# フォーメーション表示
# =========================================================

st.subheader(
    f"🧩 最終{target_n}点 "
    "フォーメーション"
)

formation_points = []

for item in formations:

    kind = item[0]

    if kind == "single":

        combo = item[1]

        bet = "-".join(
            str(x)
            for x in combo
        )

        formation_points.append(
            (
                bet,
                1
            )
        )

    else:

        # ここが重要
        # item = ("rect", best)
        # best = (a, b, c, rect)

        best = item[1]

        a = best[0]
        b = best[1]
        c = best[2]
        rect = best[3]

        bet = (
            f"{nums(a)}-"
            f"{nums(b)}-"
            f"{nums(c)}"
        )

        formation_points.append(
            (
                bet,
                len(rect)
            )
        )

# 表示
for bet, count in formation_points:

    st.write(
        f"**{bet}** → {count}点"
    )

# =========================================================
# 点数チェック
# =========================================================

formation_total = sum(
    count
    for _, count
    in formation_points
)

st.write(
    f"### 合計：{formation_total}点"
)

if formation_total == target_n:

    st.success(
        f"✅ 最終{target_n}点で一致！"
    )

else:

    # フォーメーション化が完全にまとまらない場合でも
    # 買い目自体はtarget_n点を維持
    st.warning(
        "フォーメーション表示上の組み合わせ数と"
        "最終買い目数が一致しません。"
        "上の「最終買い目」を正として扱ってください。"
    )

st.info(
    "AIは入力データを統計的に評価した参考予想です。"
    "的中を保証するものではありません。"
)
