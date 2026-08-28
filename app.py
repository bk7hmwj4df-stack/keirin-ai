import itertools
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="競輪AI v5", page_icon="🚴", layout="wide")

st.title("🚴 競輪AI v5")
st.write("競輪CSVを読み込み、選手評価→1着確率→三連単ランキング→自信度に応じて6〜12点を自動選択します。")

uploaded = st.file_uploader("📁 競輪CSVをアップロード", type=["csv"])

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

# =========================================================
# 選手評価
# =========================================================

score = df["score"].astype(float)

score_z = (
    (score - score.mean()) /
    (score.std() if score.std() > 0 else 1)
)

eval_score = score_z.copy()

if "S" in df.columns:
    eval_score += (
        (df["S"] - df["S"].mean()) /
        (df["S"].std() if df["S"].std() > 0 else 1)
    ) * 0.10

if "H" in df.columns:
    eval_score += (
        (df["H"] - df["H"].mean()) /
        (df["H"].std() if df["H"].std() > 0 else 1)
    ) * 0.12

if "B" in df.columns:
    eval_score += (
        (df["B"] - df["B"].mean()) /
        (df["B"].std() if df["B"].std() > 0 else 1)
    ) * 0.10

if "recent_win_rate" in df.columns and df["recent_win_rate"].max() > 0:
    rw = df["recent_win_rate"]

    eval_score += (
        (rw - rw.mean()) /
        (rw.std() if rw.std() > 0 else 1)
    ) * 0.18

# 脚質
if "style" in df.columns:
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
# 1着確率
# =========================================================

temperature = 1.15

x = eval_score / temperature

p = np.exp(x - x.max())
p = p / p.sum()

prob_df = pd.DataFrame({
    "rider": df["rider"],
    "ai_score": eval_score.round(3),
    "win_probability": (p * 100).round(2)
}).sort_values(
    "win_probability",
    ascending=False
)

st.subheader("🎯 AI 1着確率")
st.dataframe(prob_df, use_container_width=True)

# =========================================================
# ライン補正
# =========================================================

def line_groups(frame):

    if "line" not in frame.columns:
        return {}

    groups = {}

    for _, row in frame.iterrows():

        line = str(row["line"]).strip()

        if not line or line.lower() == "nan":
            continue

        groups.setdefault(line, []).append(
            int(row["rider"])
        )

    return groups


groups = line_groups(df)

line_bonus = {
    int(r): 1.0
    for r in df["rider"]
}

for members in groups.values():

    if len(members) >= 2:

        bonus = 1.0 + min(
            0.05,
            0.015 * (len(members) - 1)
        )

        for r in members:
            line_bonus[r] = max(
                line_bonus.get(r, 1.0),
                bonus
            )

# =========================================================
# 三連単全通り
# =========================================================

riders = df["rider"].tolist()

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

span = mx - mn if mx > mn else 1

ability = {
    r: 0.55 + 0.45 * (
        (v - mn) / span
    )
    for r, v in base.items()
}

rows = []

for a, b, c in itertools.permutations(
    riders,
    3
):

    score3 = (
        prob_map[a] ** 0.62
        * ability[b] ** 0.23
        * ability[c] ** 0.15
        * line_bonus[a]
        * line_bonus[b] ** 0.5
    )

    rows.append(
        (
            f"{a}-{b}-{c}",
            a,
            b,
            c,
            score3
        )
    )

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
).reset_index(drop=True)

tri["probability"] = (
    tri["model_score"] /
    tri["model_score"].sum()
) * 100

# =========================================================
# 自信度判定
# =========================================================

p_sorted = np.sort(p)[::-1]

top1 = float(p_sorted[0])

top2 = (
    float(p_sorted[:2].sum())
    if len(p_sorted) >= 2
    else top1
)

gap = (
    float(p_sorted[0] - p_sorted[1])
    if len(p_sorted) >= 2
    else top1
)

confidence_score = (
    top1 * 45
    + top2 * 30
    + min(gap * 100, 25)
)

# 選手数による微調整
if len(riders) <= 4:
    confidence_score += 4

elif len(riders) >= 7:
    confidence_score -= 3

confidence_score = float(
    np.clip(
        confidence_score,
        0,
        100
    )
)

# =========================================================
# 自信度 → 買い目点数
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

# 境界値は8点・10点にする
if 44 <= confidence_score < 46:
    target_n = 8

elif 36 <= confidence_score < 38:
    target_n = 10

# =========================================================
# 三連単ランキング
# =========================================================

st.subheader("🔥 AI三連単ランキング")

for i, r in tri.head(12).iterrows():

    st.write(
        f"**{i+1:02d}. {r['bet']}**  "
        f"{r['probability']:.2f}%"
    )

# =========================================================
# 最終買い目選択
# =========================================================

selected_indices = []

first_count = {}
second_count = {}

for i in tri.index:

    r = tri.loc[i]

    a = int(r["first"])
    b = int(r["second"])

    penalty = (
        1
        + 0.18 * first_count.get(a, 0)
        + 0.16 * second_count.get(b, 0)
    )

    adjusted = (
        float(r["model_score"]) /
        penalty
    )

    selected_indices.append(
        (
            adjusted,
            i
        )
    )

selected_indices.sort(
    reverse=True
)

chosen = []

first_count = {}
second_count = {}

for _, i in selected_indices:

    r = tri.loc[i]

    a = int(r["first"])
    b = int(r["second"])

    # 同じ2着への偏りを防ぐ
    if second_count.get(b, 0) >= max(
        3,
        int(np.ceil(target_n / 3))
    ):
        continue

    chosen.append(i)

    first_count[a] = (
        first_count.get(a, 0) + 1
    )

    second_count[b] = (
        second_count.get(b, 0) + 1
    )

    if len(chosen) >= target_n:
        break

# 足りない場合はランキングから補充
if len(chosen) < target_n:

    for i in tri.index:

        if i not in chosen:

            chosen.append(i)

        if len(chosen) >= target_n:
            break

top = tri.loc[chosen].copy()

top["selection_rank"] = range(
    1,
    len(top) + 1
)

# =========================================================
# 自信度表示
# =========================================================

st.subheader("🧠 レース自信度")

st.write(
    f"**{confidence_label} "
    f"自信スコア {confidence_score:.1f}/100 "
    f"→ 最終{target_n}点**"
)

# =========================================================
# 最終買い目
# =========================================================

st.subheader(
    f"💰 最終{target_n}点"
)

for i, (_, r) in enumerate(
    top.iterrows(),
    1
):

    st.write(
        f"{i}. **{r['bet']}**"
    )

# =========================================================
# フォーメーション化
# =========================================================

selected = set(
    (
        int(r["first"]),
        int(r["second"]),
        int(r["third"])
    )
    for _, r in top.iterrows()
)

remaining = set(selected)

formations = []

while remaining:

    best = None
    best_gain = 0

    # -----------------------------------------------------
    # 1着固定 × 2着複数 × 3着複数
    # -----------------------------------------------------

    for first in sorted(
        {x[0] for x in remaining}
    ):

        seconds = sorted(
            {
                x[1]
                for x in remaining
                if x[0] == first
            }
        )

        for k2 in range(
            min(3, len(seconds)),
            0,
            -1
        ):

            for bset in itertools.combinations(
                seconds,
                k2
            ):

                thirds = sorted(
                    {
                        x[2]
                        for x in remaining
                        if x[0] == first
                        and x[1] in bset
                    }
                )

                for k3 in range(
                    min(4, len(thirds)),
                    0,
                    -1
                ):

                    for cset in itertools.combinations(
                        thirds,
                        k3
                    ):

                        rect = {
                            (
                                first,
                                b,
                                c
                            )
                            for b in bset
                            for c in cset
                            if len({
                                first,
                                b,
                                c
                            }) == 3
                        }

                        if (
                            rect
                            and rect.issubset(
                                remaining
                            )
                            and len(rect) > best_gain
                        ):

                            best_gain = len(rect)

                            best = (
                                first,
                                tuple(bset),
                                tuple(cset),
                                rect
                            )

    # -----------------------------------------------------
    # 1着複数 × 2着固定 × 3着複数
    # -----------------------------------------------------

    if best is None:

        for second in sorted(
            {x[1] for x in remaining}
        ):

            firsts = sorted(
                {
                    x[0]
                    for x in remaining
                    if x[1] == second
                }
            )

            thirds = sorted(
                {
                    x[2]
                    for x in remaining
                    if x[1] == second
                }
            )

            for k1 in range(
                min(3, len(firsts)),
                0,
                -1
            ):

                for aset in itertools.combinations(
                    firsts,
                    k1
                ):

                    for k3 in range(
                        min(3, len(thirds)),
                        0,
                        -1
                    ):

                        for cset in itertools.combinations(
                            thirds,
                            k3
                        ):

                            rect = {
                                (
                                    a,
                                    second,
                                    c
                                )
                                for a in aset
                                for c in cset
                                if len({
                                    a,
                                    second,
                                    c
                                }) == 3
                            }

                            if (
                                rect
                                and rect.issubset(
                                    remaining
                                )
                                and len(rect) > best_gain
                            ):

                                best_gain = len(rect)

                                best = (
                                    tuple(aset),
                                    second,
                                    tuple(cset),
                                    rect
                                )

    # -----------------------------------------------------
    # フォーメーション決定
    # -----------------------------------------------------

    if best is None:

        x = next(iter(remaining))

        formations.append(
            (
                "single",
                x
            )
        )

        remaining.remove(x)

    else:

        formations.append(
            (
                "rect",
                best
            )
        )

        remaining -= best[3]

# =========================================================
# フォーメーション表示
# =========================================================

def nums(v):

    if isinstance(v, tuple):

        return "".join(
            str(x)
            for x in sorted(v)
        )

    return str(v)


st.subheader(
    f"🧩 最終{target_n}点をフォーメーション表示"
)

formation_points = []

for item in formations:

    if item[0] == "single":

        bet = "-".join(
            map(
                str,
                item[1]
            )
        )

        formation_points.append(
            (
                bet,
                1
            )
        )

    else:

        _, a, b, c, rect = item

        formation_points.append(
            (
                f"{nums(a)}-{nums(b)}-{nums(c)}",
                len(rect)
            )
        )

for bet, count in formation_points:

    st.write(
        f"**{bet}**　→ {count}点"
    )

formation_total = sum(
    x[1]
    for x in formation_points
)

st.caption(
    f"フォーメーション合計："
    f"{formation_total}点"
)

if formation_total == target_n:

    st.success(
        f"予想完了！ "
        f"最終{target_n}点で一致しています。"
    )

else:

    st.warning(
        "フォーメーション表示の合計点数が"
        "最終買い目数と一致していません。"
        "買い目一覧を優先してください。"
    )

st.info(
    "AIは入力データを統計的に評価した参考予想です。"
    "的中を保証するものではありません。"
)
