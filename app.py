import itertools
import re
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="競輪AI v6",
    page_icon="🚴",
    layout="wide"
)

st.title("🚴 競輪AI v6 総合データ分析型")
st.caption(
    "競走得点・戦績・脚質・S/H/B・勝率・連対率・並び・ライン・展開など、"
    "CSVに存在するデータをできるだけ総合評価します"
)

uploaded = st.file_uploader(
    "📁 競輪CSVをアップロード",
    type=["csv"]
)

if uploaded is None:
    st.info("競輪CSVをアップロードしてください。")
    st.stop()


# ==================================================
# CSV読み込み
# ==================================================

try:
    df = pd.read_csv(uploaded)
except UnicodeDecodeError:
    try:
        df = pd.read_csv(uploaded, encoding="shift_jis")
    except Exception as e:
        st.error(f"CSVを読み込めませんでした: {e}")
        st.stop()
except Exception as e:
    st.error(f"CSVを読み込めませんでした: {e}")
    st.stop()


df.columns = [
    str(c).strip().lower()
    for c in df.columns
]


# ==================================================
# 必須列確認
# ==================================================

if "rider" not in df.columns:
    st.error("rider列が必要です。")
    st.stop()


df["rider"] = pd.to_numeric(
    df["rider"],
    errors="coerce"
)

df = df.dropna(
    subset=["rider"]
).copy()

df["rider"] = df["rider"].astype(int)


if len(df) < 3:
    st.error("3人以上必要です。")
    st.stop()


if df["rider"].duplicated().any():
    st.error("rider列に重複があります。")
    st.stop()


# ==================================================
# 数値データを自動検出
#
# CSVにある数値データをできるだけ評価に使う
# ==================================================

numeric_cols = []

for col in df.columns:

    if col in ["index", "race_id", "rider"]:
        continue

    converted = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    valid_rate = converted.notna().mean()

    if valid_rate >= 0.5:
        df[col] = converted.fillna(
            converted.median()
            if converted.notna().any()
            else 0
        )

        numeric_cols.append(col)


# ==================================================
# 文字列を自動で使えるようにする
# ==================================================

for col in df.columns:

    if col in numeric_cols:
        continue

    if col in [
        "index",
        "race_id",
        "rider"
    ]:
        continue

    df[col] = df[col].astype(str)


# ==================================================
# Zスコア
# ==================================================

def zscore(series):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    std = series.std()

    if (
        pd.isna(std)
        or std == 0
    ):
        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    return (
        series - series.mean()
    ) / std


# ==================================================
# 数値データ評価
#
# 列名に応じて重要度を自動設定
# ==================================================

eval_score = pd.Series(
    np.zeros(len(df)),
    index=df.index
)


weights_used = {}


def add_score(
    column,
    weight
):

    global eval_score

    if column in df.columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

        if values.std() > 0:

            eval_score += (
                zscore(values)
                * weight
            )

            weights_used[column] = weight


# --------------------------------------------------
# 競走得点
# --------------------------------------------------

for col in [
    "score",
    "rating",
    "race_score",
    "competition_score",
    "points"
]:
    add_score(col, 1.00)


# --------------------------------------------------
# 1着率・勝率
# --------------------------------------------------

for col in [
    "win_rate",
    "recent_win_rate",
    "win",
    "first_rate",
    "1st_rate"
]:
    add_score(col, 0.70)


# --------------------------------------------------
# 連対率
# --------------------------------------------------

for col in [
    "place_rate",
    "quinella_rate",
    "top2_rate",
    "second_rate",
    "連対率"
]:
    add_score(col, 0.55)


# --------------------------------------------------
# 3連対率
# --------------------------------------------------

for col in [
    "top3_rate",
    "third_rate",
    "place3_rate",
    "三連対率"
]:
    add_score(col, 0.40)


# --------------------------------------------------
# 直近成績
# 数字が高い方が良いデータを想定
# --------------------------------------------------

for col in [
    "recent_score",
    "form",
    "recent_form",
    "momentum",
    "trend"
]:
    add_score(col, 0.45)


# --------------------------------------------------
# S
# --------------------------------------------------

for col in [
    "s",
    "st",
    "starts"
]:
    add_score(col, 0.08)


# --------------------------------------------------
# H
# --------------------------------------------------

for col in [
    "h",
    "heikou"
]:
    add_score(col, 0.08)


# --------------------------------------------------
# B
# --------------------------------------------------

for col in [
    "b",
    "back",
    "breakaway"
]:
    add_score(col, 0.12)


# --------------------------------------------------
# 決まり手
# --------------------------------------------------

for col in [
    "escape",
    "nige",
    "逃げ"
]:
    add_score(col, 0.18)


for col in [
    "makuri",
    "捲り"
]:
    add_score(col, 0.18)


for col in [
    "sashi",
    "差し"
]:
    add_score(col, 0.14)


for col in [
    "mark",
    "マーク"
]:
    add_score(col, 0.10)


# --------------------------------------------------
# その他の数値データ
#
# 上で使われていないものも少し評価
# --------------------------------------------------

for col in numeric_cols:

    if col not in weights_used:

        values = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

        if values.std() > 0:

            eval_score += (
                zscore(values)
                * 0.05
            )

            weights_used[col] = 0.05


# ==================================================
# 着順系データ
#
# 数字が小さいほど良い場合は逆評価
# ==================================================

lower_is_better_cols = [

    "average_finish",
    "avg_finish",
    "recent_rank",
    "rank",
    "着順",
    "平均着順"

]


for col in lower_is_better_cols:

    if col in df.columns:

        values = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(
            df[col].median()
        )

        if values.std() > 0:

            eval_score += (
                -zscore(values)
                * 0.45
            )

            weights_used[col] = -0.45


# ==================================================
# ライン解析
# ==================================================

line_map = {}

if "line" in df.columns:

    for _, row in df.iterrows():

        rider = int(row["rider"])

        line_text = str(
            row["line"]
        ).strip()

        nums = re.findall(
            r"\d+",
            line_text
        )

        nums = [
            int(x)
            for x in nums
        ]

        if rider not in nums:
            nums.insert(
                0,
                rider
            )

        line_map[rider] = nums


# --------------------------------------------------
# 同じラインの人数
# --------------------------------------------------

line_size = {}

for rider in df["rider"]:

    if rider in line_map:

        line_size[rider] = len(
            line_map[rider]
        )

    else:

        line_size[rider] = 1


# ==================================================
# 脚質解析
# ==================================================

style_map = {}

if "style" in df.columns:

    for _, row in df.iterrows():

        style_map[
            int(row["rider"])
        ] = str(
            row["style"]
        ).strip()


# ==================================================
# ライン・脚質ボーナス
# ==================================================

riders = df["rider"].tolist()

for rider in riders:

    idx = df[
        df["rider"] == rider
    ].index[0]

    style = style_map.get(
        rider,
        ""
    )

    size = line_size.get(
        rider,
        1
    )


    # ライン人数
    if size >= 3:

        eval_score.loc[idx] += 0.10

    elif size == 2:

        eval_score.loc[idx] += 0.04


    # 脚質
    if style in [
        "逃",
        "逃げ"
    ]:

        if size >= 2:
            eval_score.loc[idx] += 0.08

    elif style in [
        "追",
        "追込"
    ]:

        if size >= 2:
            eval_score.loc[idx] += 0.07


df["ai_eval"] = eval_score


# ==================================================
# 1着能力
# ==================================================

temperature = 1.35

x = eval_score / temperature

p = np.exp(
    x - x.max()
)

p = p / p.sum()


prob_map = dict(
    zip(
        df["rider"],
        p
    )
)


eval_map = dict(
    zip(
        df["rider"],
        eval_score
    )
)


# ==================================================
# ライン先頭判定
# ==================================================

line_front = {}

for rider in riders:

    if rider in line_map:

        nums = line_map[rider]

        if len(nums) > 0:

            line_front[rider] = nums[0]

    else:

        line_front[rider] = rider


# ==================================================
# 各選手の役割を自動判定
# ==================================================

role_score = {}

for rider in riders:

    score = 0

    style = style_map.get(
        rider,
        ""
    )

    if style in [
        "逃",
        "逃げ"
    ]:
        score += 0.50

    if style in [
        "両",
        "自在"
    ]:
        score += 0.35

    if style in [
        "追",
        "追込"
    ]:
        score += 0.15


    # B・Hがあれば積極性評価
    idx = df[
        df["rider"] == rider
    ].index[0]

    if "b" in df.columns:

        role_score_b = zscore(
            df["b"]
        ).loc[idx]

        score += (
            role_score_b
            * 0.10
        )

    if "h" in df.columns:

        role_score_h = zscore(
            df["h"]
        ).loc[idx]

        score += (
            role_score_h
            * 0.08
        )


    role_score[rider] = score


# ==================================================
# 展開パターン作成
#
# 先行
# 捲り
# 番手差し
# 混戦
# ==================================================

styles = [

    "先行",
    "捲り",
    "番手",
    "混戦"

]


style_weights = {

    "先行": 0.28,

    "捲り": 0.27,

    "番手": 0.27,

    "混戦": 0.18

}


# ==================================================
# 展開別 三連単評価
# ==================================================

rows = []


for first, second, third in itertools.permutations(
    riders,
    3
):

    total_score = 0


    for race_style in styles:

        score = 0


        # --------------------------
        # 基礎能力
        # --------------------------

        score += (
            prob_map[first]
            * 0.52
        )

        score += (
            prob_map[second]
            * 0.30
        )

        score += (
            prob_map[third]
            * 0.18
        )


        # --------------------------
        # 先行展開
        # --------------------------

        if race_style == "先行":

            if line_front.get(
                first
            ) == first:

                score += 0.20

            if role_score.get(
                first,
                0
            ) > 0.25:

                score += 0.10

            if (
                second in line_map.get(
                    first,
                    []
                )
            ):
                score += 0.10


        # --------------------------
        # 捲り展開
        # --------------------------

        elif race_style == "捲り":

            style = style_map.get(
                first,
                ""
            )

            if style in [
                "両",
                "自在"
            ]:
                score += 0.16

            if role_score.get(
                first,
                0
            ) > 0.20:

                score += 0.08


        # --------------------------
        # 番手展開
        # --------------------------

        elif race_style == "番手":

            first_line = line_map.get(
                first,
                []
            )

            second_line = line_map.get(
                second,
                []
            )


            if (
                first in second_line
                and len(second_line) >= 2
            ):

                score += 0.18


            if (
                second in first_line
            ):

                score += 0.08


        # --------------------------
        # 混戦
        # --------------------------

        elif race_style == "混戦":

            ability_gap = (
                prob_map[first]
                - prob_map[second]
            )

            if ability_gap < 0.10:
                score += 0.08


        total_score += (
            score
            * style_weights[race_style]
        )


    # ==============================================
    # ライン関係
    # ==============================================

    first_line = line_map.get(
        first,
        [first]
    )


    # 同ラインワンツー
    if second in first_line:

        total_score *= 1.15


    # 同ライン123
    if (
        second in first_line
        and third in first_line
    ):

        total_score *= 1.08


    # ==============================================
    # 2番手・3番手からの逆転
    #
    # 1着固定防止
    # ==============================================

    if (
        prob_map[second]
        >= prob_map[first] * 0.80
    ):

        total_score *= 1.06


    if (
        prob_map[third]
        >= prob_map[first] * 0.88
    ):

        total_score *= 1.03


    rows.append(
        (
            first,
            second,
            third,
            total_score
        )
    )


# ==================================================
# 三連単ランキング
# ==================================================

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


# ==================================================
# AI自信度
# ==================================================

sorted_tri = tri[
    "probability"
].to_numpy()


top_prob = sorted_tri[0]

second_prob = (
    sorted_tri[1]
    if len(sorted_tri) > 1
    else 0
)


spread = (
    top_prob
    - second_prob
)


# 上位候補の集中度
top12_share = (
    tri.head(12)["probability"]
    .sum()
)


# ==================================================
# 点数決定
#
# 自信度が高い → 少ない
# 混戦 → 多い
# ==================================================

if (
    top_prob >= 1.80
    and spread >= 0.35
):

    target_points = 6
    confidence = "★★★★★"

elif (
    top_prob >= 1.40
    and spread >= 0.20
):

    target_points = 8
    confidence = "★★★★☆"

elif (
    top_prob >= 1.10
    and spread >= 0.10
):

    target_points = 10
    confidence = "★★★☆☆"

else:

    target_points = 12
    confidence = "★★☆☆☆"


# ==================================================
# 最終買い目選択
#
# 1着を基本1〜2人
# ただし展開が混戦なら自然に広げる
# ==================================================

pool = tri.head(
    min(
        len(tri),
        target_points * 6
    )
).copy()


selected_rows = []

selected_set = set()


# ==================================================
# 1着候補
# ==================================================

first_rank = (

    tri.groupby("first")
    ["model_score"]

    .sum()

    .sort_values(
        ascending=False
    )

)


top_firsts = (
    first_rank
    .head(3)
    .index
    .tolist()
)


# ==================================================
# まず1着候補を確保
# ==================================================

if target_points <= 8:

    required_firsts = top_firsts[:2]

else:

    required_firsts = top_firsts[:3]


for first in required_firsts:

    candidates = pool[
        pool["first"] == first
    ]

    if len(candidates) > 0:

        row = candidates.iloc[0]

        key = (

            int(row["first"]),
            int(row["second"]),
            int(row["third"])

        )

        if key not in selected_set:

            selected_rows.append(row)

            selected_set.add(key)


# ==================================================
# 残りは総合評価順
# ==================================================

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


# ==================================================
# 点数不足時
# ==================================================

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


# ==================================================
# 最終買い目
# ==================================================

selected_df = pd.DataFrame(
    selected_rows
)


selected_df = selected_df.sort_values(
    "model_score",
    ascending=False
).reset_index(drop=True)


# ==================================================
# フォーメーション変換
#
# 選んだ買い目以外を勝手に増やさない
# ==================================================

selected = {

    (

        int(row["first"]),
        int(row["second"]),
        int(row["third"])

    )

    for _, row in selected_df.iterrows()

}


def make_label(values):

    return "".join(

        str(x)

        for x in sorted(values)

    )


def get_combo_count(
    firsts,
    seconds,
    thirds
):

    combos = set()


    for a in firsts:

        for b in seconds:

            for c in thirds:

                if len(
                    {a, b, c}
                ) == 3:

                    combos.add(
                        (a, b, c)
                    )


    return combos


def find_best_formation(
    remaining
):

    first_values = sorted(
        {
            x[0]
            for x in remaining
        }
    )


    second_values = sorted(
        {
            x[1]
            for x in remaining
        }
    )


    third_values = sorted(
        {
            x[2]
            for x in remaining
        }
    )


    best = None
    best_score = None


    for fa in range(
        1,
        min(3, len(first_values)) + 1
    ):

        for firsts in itertools.combinations(
            first_values,
            fa
        ):

            for sa in range(
                1,
                min(4, len(second_values)) + 1
            ):

                for seconds in itertools.combinations(
                    second_values,
                    sa
                ):

                    for ta in range(
                        1,
                        min(5, len(third_values)) + 1
                    ):

                        for thirds in itertools.combinations(
                            third_values,
                            ta
                        ):

                            combos = get_combo_count(
                                firsts,
                                seconds,
                                thirds
                            )


                            if len(combos) < 2:
                                continue


                            if not combos.issubset(
                                remaining
                            ):
                                continue


                            # 複数の1着を優先
                            first_bonus = (

                                2
                                if len(firsts) >= 2
                                else 0

                            )


                            second_bonus = (

                                1
                                if len(seconds) >= 2
                                else 0

                            )


                            compactness = (

                                len(firsts)
                                + len(seconds)
                                + len(thirds)

                            )


                            score = (

                                len(combos),

                                first_bonus,

                                second_bonus,

                                -compactness

                            )


                            if (
                                best_score is None
                                or score > best_score
                            ):

                                best_score = score

                                best = (

                                    firsts,

                                    seconds,

                                    thirds,

                                    combos

                                )


    return best


# ==================================================
# フォーメーション生成
# ==================================================

remaining = set(selected)

formations = []


while remaining:

    best = find_best_formation(
        remaining
    )


    if best is None:

        item = next(
            iter(remaining)
        )


        formations.append(

            (

                (item[0],),

                (item[1],),

                (item[2],),

                {item}

            )

        )


        remaining.remove(
            item
        )


    else:

        firsts, seconds, thirds, combos = best


        formations.append(

            (

                firsts,

                seconds,

                thirds,

                combos

            )

        )


        remaining -= combos


# ==================================================
# 表示
# ==================================================

st.subheader("📊 使用データ")


used_data = pd.DataFrame({

    "項目": list(
        weights_used.keys()
    ),

    "重要度": list(
        weights_used.values()
    )

})


st.dataframe(
    used_data,
    use_container_width=True
)


st.subheader("🎯 AI 1着評価")


prob_df = pd.DataFrame({

    "車番": riders,

    "総合AI評価": [

        eval_map[r]
        for r in riders

    ],

    "1着確率": [

        prob_map[r] * 100
        for r in riders

    ],

    "ライン人数": [

        line_size.get(r, 1)
        for r in riders

    ],

    "脚質": [

        style_map.get(r, "")
        for r in riders

    ]

})


prob_df = prob_df.sort_values(
    "1着確率",
    ascending=False
)


st.dataframe(

    prob_df.style.format({

        "総合AI評価": "{:.3f}",

        "1着確率": "{:.2f}%"

    }),

    use_container_width=True

)


# ==================================================
# 自信度
# ==================================================

st.subheader("🔥 AI自信度")

st.write(
    f"### {confidence}"
)

st.write(
    f"最終買い目：**{target_points}点**"
)


# ==================================================
# 三連単ランキング
# ==================================================

st.subheader("🏆 三連単ランキング")


for i, row in tri.head(15).iterrows():

    st.write(

        f"**{i + 1}. "
        f"{row['bet']}**　"
        f"{row['probability']:.2f}%"

    )


# ==================================================
# 最終買い目
# ==================================================

st.subheader(
    f"💰 最終買い目 {target_points}点"
)


for i, row in selected_df.iterrows():

    st.write(

        f"{i + 1}. "
        f"**{row['bet']}**"

    )


# ==================================================
# 最終フォーメーション
# ==================================================

st.subheader(
    "🧩 最終フォーメーション"
)


total_points = 0


for firsts, seconds, thirds, combos in formations:

    label = (

        f"{make_label(firsts)}"

        f"-"

        f"{make_label(seconds)}"

        f"-"

        f"{make_label(thirds)}"

    )


    count = len(combos)

    total_points += count


    st.write(

        f"### {label}　"

        f"**{count}点**"

    )


st.caption(

    f"フォーメーション合計："
    f"{total_points}点"

)


# ==================================================
# 最終結論
# ==================================================

st.success("予想完了！")


st.subheader("🏁 最終結論")


final_text = "　".join(

    [

        f"{make_label(firsts)}-"
        f"{make_label(seconds)}-"
        f"{make_label(thirds)}"

        for firsts, seconds, thirds, combos

        in formations

    ]

)


st.write(
    f"## {final_text}"
)


st.info(
    "CSVに存在するデータを自動検出して総合評価します。"
    "ただし、CSVに入っていない情報は自動では判断できません。"
)
