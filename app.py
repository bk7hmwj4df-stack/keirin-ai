# -*- coding: utf-8 -*-
import re
import math
import streamlit as st
from itertools import permutations

# ==================================================
# 設定
# ==================================================
st.set_page_config(
    page_title="🐎 競馬AIフォーメーション予想",
    page_icon="🐎",
    layout="wide"
)

st.title("🐎 競馬AIフォーメーション予想")
st.caption("競走能力 × 過去戦績 × 調教 × 血統 × 距離適性 × 馬場適性 × 騎手 × 展開")

st.info(
    "基本データだけでも予想できます。"
    "過去戦績・調教などを追加すると評価精度を上げられます。"
)

# ==================================================
# 入力
# ==================================================

st.subheader("① 出馬表")

default_horses = """1 ロマンス 68.4 55.0 9
2 オーパ 209.7 54.0 14
3 ネイティヴプライド 26.0 57.0 8
4 ダイヒョウカーク 125.0 57.0 10
5 プリヴィマーク 184.0 57.0 13
6 ゴールドプレイヤー 4.0 57.0 3
7 エターナルホープ 3.7 57.0 2
8 オウケンサクラコ 17.0 57.0 5
9 マーゴットライス 22.2 57.0 7
10 アデルフィー 4.5 57.0 4
11 スビアーノ 151.2 55.0 11
12 バターショコラ 173.7 55.0 12
13 ハチマン 461.4 54.0 15
14 14番馬 0.0 0.0 0
15 カシマライフウ 3.6 57.0 1"""

horses_text = st.text_area(
    "馬データ",
    value=default_horses,
    height=430,
    help="馬番 馬名 単勝オッズ 斤量 人気"
)

# ==================================================
# レース条件
# ==================================================

st.subheader("② レース条件")

col1, col2, col3, col4 = st.columns(4)

with col1:
    course = st.selectbox(
        "競馬場",
        ["東京", "中山", "阪神", "京都", "中京",
         "新潟", "福島", "札幌", "函館", "小倉"]
    )

with col2:
    distance = st.number_input(
        "距離（m）",
        min_value=1000,
        max_value=3600,
        value=1600,
        step=100
    )

with col3:
    surface = st.selectbox(
        "馬場",
        ["芝", "ダート"]
    )

with col4:
    track_condition = st.selectbox(
        "馬場状態",
        ["良", "稍重", "重", "不良"]
    )

# ==================================================
# 詳細評価入力
# ==================================================

st.subheader("③ 詳細データ")

st.caption(
    "各項目は1〜100点。"
    "分からない馬は空欄のままでOK。"
)

default_detail = """1 50 50 50 50 50 50 50
2 40 45 40 45 40 40 45
3 60 55 60 65 60 55 60
4 45 50 50 45 50 50 50
5 40 40 45 40 45 45 45
6 80 75 70 80 75 85 75
7 82 80 75 85 80 80 82
8 68 70 65 70 65 65 70
9 65 60 65 65 60 65 68
10 78 75 75 80 75 80 80
11 45 45 45 50 50 45 45
12 40 45 45 40 45 40 45
13 35 35 35 35 35 35 40
14 50 50 50 50 50 50 50
15 88 85 82 90 85 90 88"""

details_text = st.text_area(
    "馬番 過去戦績 調教 血統 距離適性 馬場適性 騎手 展開",
    value=default_detail,
    height=430,
    help=(
        "例："
        "6 80 75 70 80 75 85 75"
    )
)

# ==================================================
# 配点設定
# ==================================================

st.subheader("④ AIの分析比率")

c1, c2, c3, c4 = st.columns(4)

with c1:
    w_form = st.slider("過去戦績", 0, 30, 20)

with c2:
    w_training = st.slider("調教", 0, 30, 15)

with c3:
    w_blood = st.slider("血統", 0, 30, 10)

with c4:
    w_distance = st.slider("距離適性", 0, 30, 15)

c5, c6, c7, c8 = st.columns(4)

with c5:
    w_track = st.slider("馬場適性", 0, 30, 10)

with c6:
    w_jockey = st.slider("騎手", 0, 30, 15)

with c7:
    w_pace = st.slider("展開", 0, 30, 15)

with c8:
    point_count = st.selectbox(
        "買い目点数",
        [10, 12, 14, 16, 18, 20, 24],
        index=1
    )

# ==================================================
# データ解析
# ==================================================

def parse_horses(text):

    horses = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 5:
            continue

        try:
            number = int(parts[0])
            horse_name = parts[1]
            odds = float(parts[2])
            weight = float(parts[3])
            popularity = int(parts[4])

        except:
            continue

        horses[number] = {
            "number": number,
            "name": horse_name,
            "odds": odds,
            "weight": weight,
            "popularity": popularity
        }

    return horses


def parse_details(text):

    details = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 8:
            continue

        try:

            number = int(parts[0])

            values = list(
                map(float, parts[1:8])
            )

            details[number] = {
                "form": values[0],
                "training": values[1],
                "blood": values[2],
                "distance": values[3],
                "track": values[4],
                "jockey": values[5],
                "pace": values[6]
            }

        except:
            continue

    return details


# ==================================================
# オッズ評価
# ==================================================

def odds_score(odds):

    if odds <= 0:
        return 50

    # オッズが低いほど高評価
    score = 100 - (
        math.log(max(odds, 1.01)) * 22
    )

    return max(20, min(100, score))


# ==================================================
# 斤量補正
# ==================================================

def weight_score(weight):

    if weight <= 0:
        return 50

    # 57kgを基準
    score = 100 - abs(weight - 57.0) * 8

    return max(40, min(100, score))


# ==================================================
# 総合評価
# ==================================================

def calculate_strengths(
    horses,
    details
):

    strengths = {}

    total_weight = (
        w_form
        + w_training
        + w_blood
        + w_distance
        + w_track
        + w_jockey
        + w_pace
    )

    if total_weight == 0:
        total_weight = 1

    for number, horse in horses.items():

        detail = details.get(
            number,
            {
                "form": 50,
                "training": 50,
                "blood": 50,
                "distance": 50,
                "track": 50,
                "jockey": 50,
                "pace": 50
            }
        )

        performance_score = (
            detail["form"] * w_form
            + detail["training"] * w_training
            + detail["blood"] * w_blood
            + detail["distance"] * w_distance
            + detail["track"] * w_track
            + detail["jockey"] * w_jockey
            + detail["pace"] * w_pace
        ) / total_weight

        odds_component = odds_score(
            horse["odds"]
        )

        weight_component = weight_score(
            horse["weight"]
        )

        # ----------------------------
        # 最終AIスコア
        # ----------------------------

        final_score = (
            performance_score * 0.80
            + odds_component * 0.12
            + weight_component * 0.08
        )

        strengths[number] = {
            "total": final_score,
            "performance": performance_score,
            "detail": detail
        }

    return strengths


# ==================================================
# 三連単候補生成
# ==================================================

def make_combinations(
    horses,
    strengths,
    limit
):

    ranked = sorted(
        strengths.keys(),
        key=lambda x: strengths[x]["total"],
        reverse=True
    )

    # 上位7頭を中心
    main = ranked[:7]

    combinations = []

    for a, b, c in permutations(main, 3):

        score = (
            strengths[a]["total"] * 0.50
            + strengths[b]["total"] * 0.32
            + strengths[c]["total"] * 0.18
        )

        # 1着適性
        score += (
            strengths[a]["detail"]["pace"]
            * 0.08
        )

        # 騎手能力
        score += (
            strengths[b]["detail"]["jockey"]
            * 0.04
        )

        combinations.append(
            ((a, b, c), score)
        )

    combinations.sort(
        key=lambda x: x[1],
        reverse=True
    )

    selected = []

    for combo, score in combinations:

        if combo not in selected:

            selected.append(combo)

        if len(selected) >= limit:
            break

    return selected, ranked


# ==================================================
# フォーメーション表示
# ==================================================

def make_formation(combos):

    first = []
    second = []
    third = []

    for a, b, c in combos:

        if a not in first:
            first.append(a)

        if b not in second:
            second.append(b)

        if c not in third:
            third.append(c)

    return (
        f"{''.join(map(str, first))}"
        f"-"
        f"{''.join(map(str, second))}"
        f"-"
        f"{''.join(map(str, third))}"
    )


def compress_combos(combos):

    groups = {}

    for a, b, c in combos:

        groups.setdefault(a, {})
        groups[a].setdefault(b, [])
        groups[a][b].append(c)

    result = []

    for a in groups:

        for b in groups[a]:

            cs = groups[a][b]

            result.append(
                f"{a}-{b}-"
                f"{''.join(map(str, sorted(cs)))}"
            )

    return result


# ==================================================
# 予想実行
# ==================================================

if st.button(
    "🔥 AIがガチ分析する",
    use_container_width=True
):

    horses = parse_horses(
        horses_text
    )

    details = parse_details(
        details_text
    )

    if len(horses) < 3:

        st.error(
            "最低3頭以上の馬データが必要です。"
        )

        st.stop()

    strengths = calculate_strengths(
        horses,
        details
    )

    combos, ranked = make_combinations(
        horses,
        strengths,
        point_count
    )

    st.success(
        "AI分析完了！"
    )

    # ==================================================
    # 本命
    # ==================================================

    st.divider()

    st.subheader(
        "🏆 AI最終フォーメーション"
    )

    st.code(
        make_formation(combos)
    )

    st.caption(
        f"合計：{len(combos)}点"
    )

    st.divider()

    # ==================================================
    # 買い目
    # ==================================================

    st.subheader(
        "🎯 実際の買い目"
    )

    for combo in compress_combos(combos):

        st.code(combo)

    # ==================================================
    # ランキング
    # ==================================================

    st.divider()

    st.subheader(
        "🔥 馬別総合評価"
    )

    for rank, number in enumerate(
        ranked[:10],
        start=1
    ):

        horse = horses[number]
        strength = strengths[number]

        st.write(
            f"**{rank}位："
            f"{number}番 "
            f"{horse['name']}**"
        )

        st.write(
            f"総合評価："
            f"**{strength['total']:.1f}点**"
        )

        st.caption(
            f"過去戦績 "
            f"{strength['detail']['form']:.0f} ｜ "
            f"調教 "
            f"{strength['detail']['training']:.0f} ｜ "
            f"血統 "
            f"{strength['detail']['blood']:.0f} ｜ "
            f"距離 "
            f"{strength['detail']['distance']:.0f} ｜ "
            f"馬場 "
            f"{strength['detail']['track']:.0f} ｜ "
            f"騎手 "
            f"{strength['detail']['jockey']:.0f} ｜ "
            f"展開 "
            f"{strength['detail']['pace']:.0f}"
        )

    # ==================================================
    # 分析
    # ==================================================

    st.divider()

    st.subheader(
        "🐎 AI分析条件"
    )

    st.write(
        f"競馬場：{course} ｜ "
        f"距離：{distance}m ｜ "
        f"{surface} ｜ "
        f"馬場：{track_condition}"
    )

    st.warning(
        "⚠️ 現在は出馬表に加えて、"
        "過去戦績・調教・血統・距離適性・馬場適性・"
        "騎手・展開を評価できる競馬AIです。"
        "詳細データを正確に入力するほど予想精度が上がります。"
    )

    # ==================================================
    # 穴馬
    # ==================================================

    st.divider()

    st.subheader(
        "💣 AI穴馬候補"
    )

    longshots = sorted(
        horses.keys(),
        key=lambda x: (
            strengths[x]["total"]
            / max(horses[x]["popularity"], 1)
        ),
        reverse=True
    )

    shown = 0

    for number in longshots:

        if horses[number]["popularity"] >= 6:

            horse = horses[number]

            st.write(
                f"💣 {number}番 "
                f"{horse['name']} "
                f"｜総合 "
                f"{strengths[number]['total']:.1f}点 "
                f"｜{horse['popularity']}番人気"
            )

            shown += 1

        if shown >= 3:
            break
