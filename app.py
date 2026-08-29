# -*- coding: utf-8 -*-

import re
import streamlit as st
from itertools import product

# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="🚴 競輪AI フォーメーション予想",
    page_icon="🚴",
    layout="wide",
)

st.title("🚴 競輪AI ガチフォーメーション予想")
st.caption(
    "無料版：選手・並び・競走得点を入力すると、ラインと展開から三連単フォーメーションを自動作成します。"
)

# =========================================================
# ユーザーの予想ルール
# =========================================================

st.info(
    """
【予想ルール】

・競走得点だけで決めない  
・ライン構成を重視  
・先行選手の主導権争いを考える  
・番手選手の差し切りも評価  
・1着候補は原則2人程度  
・1着2着を同じセットで固定しすぎない  
・普通で見やすいフォーメーション  
・必ず指定点数以内  
"""
)

# =========================================================
# 基本設定
# =========================================================

col1, col2 = st.columns(2)

with col1:
    race_name = st.text_input(
        "レース名",
        placeholder="例：高松競輪 5R"
    )

with col2:
    target_points = st.selectbox(
        "買い目点数",
        options=list(range(6, 21)),
        index=6,
        format_func=lambda x: f"{x}点"
    )

# =========================================================
# 簡単入力
# =========================================================

st.subheader("🏁 選手データをコピペ")

st.caption("このままコピペでOK。脚質は 逃・両・追 のどれか。")

default_riders = """1 久木原洋 101.61 追
2 泉慶輔 95.03 追
3 横関裕樹 101.55 両
4 島田竜二 94.38 追
5 佐藤雅春 96.91 追
6 飯嶋則之 90.76 追
7 野口裕史 101.53 逃
8 下井竜 93.18 逃
9 角田光 95.37 逃"""

riders_text = st.text_area(
    "選手データ",
    value=default_riders,
    height=280
)

st.subheader("➡️ 並び")

lines_text = st.text_area(
    "ライン構成",
    value="""9-5-2
7-1-6
4
8-3""",
    height=180
)

st.caption(
    "例：9-5-2 のように入力。単騎は 4 のように1人だけ入力。"
)

# =========================================================
# 直近調子
# =========================================================

with st.expander("🔥 直近の調子を調整（任意）"):

    st.caption(
        "調子が良い選手は +2、悪い選手は -2 など。"
    )

    form_text = st.text_area(
        "例：7 +2 / 1 +1 / 3 +2 / 9 -1",
        placeholder="例：7 +2 / 1 +1 / 3 -1",
        height=100
    )

# =========================================================
# 選手データ解析
# =========================================================

def parse_riders(text):

    riders = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        pattern = r"^(\d+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([逃両追])"

        match = re.search(pattern, line)

        if match:

            number = int(match.group(1))
            name = match.group(2).strip()
            score = float(match.group(3))
            style = match.group(4)

            riders[number] = {
                "number": number,
                "name": name,
                "score": score,
                "style": style,
            }

    return riders


# =========================================================
# ライン解析
# =========================================================

def parse_lines(text):

    lines = []

    for raw_line in text.splitlines():

        raw_line = raw_line.strip()

        if not raw_line:
            continue

        numbers = re.findall(r"\d+", raw_line)

        if numbers:

            line = [int(x) for x in numbers]

            lines.append(line)

    return lines


# =========================================================
# 調子解析
# =========================================================

def parse_form(text):

    form = {}

    matches = re.findall(
        r"(\d+)\s*([+-]\s*\d+(?:\.\d+)?)",
        text
    )

    for number, value in matches:

        value = value.replace(" ", "")

        form[int(number)] = float(value)

    return form


# =========================================================
# 選手能力計算
# =========================================================

def calculate_ratings(riders, lines, form):

    ratings = {}

    # 得点の範囲を確認
    scores = [r["score"] for r in riders.values()]

    if not scores:
        return {}

    min_score = min(scores)
    max_score = max(scores)

    score_range = max(max_score - min_score, 1)

    for number, rider in riders.items():

        # 競走得点
        base = (
            (rider["score"] - min_score)
            / score_range
            * 60
        )

        # 基礎点
        rating = 40 + base

        # 脚質補正
        if rider["style"] == "逃":
            rating += 3

        elif rider["style"] == "両":
            rating += 4

        elif rider["style"] == "追":
            rating += 1

        # 調子補正
        rating += form.get(number, 0) * 3

        ratings[number] = {
            "base": rating,
            "first": rating,
            "second": rating,
            "third": rating,
        }

    # -----------------------------------------------------
    # ライン補正
    # -----------------------------------------------------

    for line in lines:

        if not line:
            continue

        for position, number in enumerate(line):

            if number not in ratings:
                continue

            rider = riders[number]

            # 先頭
            if position == 0:

                if rider["style"] == "逃":

                    ratings[number]["first"] += 7
                    ratings[number]["second"] += 3

                elif rider["style"] == "両":

                    ratings[number]["first"] += 6
                    ratings[number]["second"] += 4

                else:

                    ratings[number]["first"] += 2

            # 番手
            elif position == 1:

                ratings[number]["second"] += 9
                ratings[number]["first"] += 5
                ratings[number]["third"] += 6

            # 3番手
            else:

                ratings[number]["third"] += 8
                ratings[number]["second"] += 3

        # ラインが長いほど有利
        if len(line) >= 3:

            for number in line:

                if number in ratings:

                    ratings[number]["second"] += 2
                    ratings[number]["third"] += 2

    # -----------------------------------------------------
    # 逃げ選手が複数いる場合
    # -----------------------------------------------------

    leaders = []

    for line in lines:

        if not line:
            continue

        first = line[0]

        if (
            first in riders
            and riders[first]["style"] in ["逃", "両"]
        ):
            leaders.append(first)

    # 先行候補が多いなら番手有利
    if len(leaders) >= 3:

        for line in lines:

            if len(line) >= 2:

                second = line[1]

                if second in ratings:

                    ratings[second]["first"] += 3
                    ratings[second]["second"] += 5

    return ratings


# =========================================================
# 三連単候補生成
# =========================================================

def generate_trifecta(ratings, target_points):

    numbers = list(ratings.keys())

    candidates = []

    for a, b, c in product(numbers, repeat=3):

        if len({a, b, c}) < 3:
            continue

        value = (
            ratings[a]["first"] * 0.48
            + ratings[b]["second"] * 0.32
            + ratings[c]["third"] * 0.20
        )

        candidates.append(
            {
                "ticket": (a, b, c),
                "value": value
            }
        )

    candidates.sort(
        key=lambda x: x["value"],
        reverse=True
    )

    # -----------------------------------------------------
    # 1着候補を原則2人に絞る
    # -----------------------------------------------------

    first_rank = sorted(
        numbers,
        key=lambda x: ratings[x]["first"],
        reverse=True
    )

    first_candidates = first_rank[:2]

    # -----------------------------------------------------
    # 本命候補を抽出
    # -----------------------------------------------------

    filtered = []

    for item in candidates:

        a, b, c = item["ticket"]

        if a in first_candidates:
            filtered.append(item)

    # -----------------------------------------------------
    # 1着2着固定の繰り返しを避ける
    # -----------------------------------------------------

    selected = []

    pair_count = {}

    for item in filtered:

        if len(selected) >= target_points:
            break

        a, b, c = item["ticket"]

        pair = (a, b)

        # 同じ1着2着は最大2回まで
        if pair_count.get(pair, 0) >= 2:
            continue

        selected.append(item)

        pair_count[pair] = (
            pair_count.get(pair, 0) + 1
        )

    # -----------------------------------------------------
    # 足りない場合
    # -----------------------------------------------------

    if len(selected) < target_points:

        for item in filtered:

            if item not in selected:

                selected.append(item)

            if len(selected) >= target_points:
                break

    return selected[:target_points]


# =========================================================
# フォーメーション形式に変換
# =========================================================

def format_tickets(tickets):

    if not tickets:
        return ""

    # 1着ごとに分類
    groups = {}

    for a, b, c in tickets:

        groups.setdefault(a, [])

        groups[a].append((b, c))

    results = []

    for first, pairs in groups.items():

        second_dict = {}

        for second, third in pairs:

            second_dict.setdefault(second, [])

            second_dict[second].append(third)

        for second, thirds in second_dict.items():

            thirds = sorted(set(thirds))

            third_text = "".join(
                str(x) for x in thirds
            )

            results.append(
                f"{first}-{second}-{third_text}"
            )

    return results


# =========================================================
# 分析実行
# =========================================================

if st.button(
    "🔥 ガチフォーメーション予想する",
    type="primary",
    use_container_width=True
):

    riders = parse_riders(riders_text)
    lines = parse_lines(lines_text)
    form = parse_form(form_text)

    if len(riders) < 3:

        st.error(
            "選手データを最低3人入力してください。"
        )

        st.stop()

    if not race_name.strip():

        race_name = "競輪レース"

    # 能力計算
    ratings = calculate_ratings(
        riders,
        lines,
        form
    )

    # 三連単生成
    tickets_data = generate_trifecta(
        ratings,
        target_points
    )

    tickets = [
        x["ticket"]
        for x in tickets_data
    ]

    # =====================================================
    # 印
    # =====================================================

    first_rank = sorted(
        riders.keys(),
        key=lambda x: ratings[x]["first"],
        reverse=True
    )

    second_rank = sorted(
        riders.keys(),
        key=lambda x: ratings[x]["second"],
        reverse=True
    )

    # =====================================================
    # 結果表示
    # =====================================================

    st.divider()

    st.header(f"🔥 {race_name} 最終予想")

    st.subheader("【AI結論】")

    labels = ["◎", "○", "▲", "☆"]

    cols = st.columns(4)

    for i in range(4):

        if i < len(first_rank):

            number = first_rank[i]

            with cols[i]:

                st.metric(
                    labels[i],
                    f"{number} {riders[number]['name']}"
                )

    # -----------------------------------------------------
    # 選手評価
    # -----------------------------------------------------

    st.subheader("【選手評価】")

    ranking = sorted(
        riders.keys(),
        key=lambda x: ratings[x]["first"],
        reverse=True
    )

    for number in ranking:

        rider = riders[number]

        st.write(
            f"**{number} {rider['name']}** "
            f"｜得点 {rider['score']} "
            f"｜脚質 {rider['style']}"
        )

    # -----------------------------------------------------
    # 展開
    # -----------------------------------------------------

    st.subheader("【想定展開】")

    if lines:

        main_lines = sorted(
            lines,
            key=lambda line: sum(
                ratings[n]["base"]
                for n in line
                if n in ratings
            ),
            reverse=True
        )

        for i, line in enumerate(main_lines):

            line_text = "-".join(
                str(x) for x in line
            )

            if i == 0:

                st.write(
                    f"・本線は **{line_text}** が中心"
                )

            elif i == 1:

                st.write(
                    f"・対抗ライン **{line_text}** の捲り警戒"
                )

            else:

                st.write(
                    f"・穴として **{line_text}** も注意"
                )

    # -----------------------------------------------------
    # 買い目
    # -----------------------------------------------------

    st.divider()

    st.header("🎯 最終フォーメーション")

    formation = format_tickets(tickets)

    for text in formation:

        st.code(text, language=None)

    st.success(
        f"合計：{len(tickets)}点"
    )

    # -----------------------------------------------------
    # 実際の買い目
    # -----------------------------------------------------

    with st.expander("実際の買い目を全部確認"):

        for a, b, c in tickets:

            st.write(
                f"**{a}-{b}-{c}**"
            )

# =========================================================
# 注意
# =========================================================

st.divider()

st.caption(
    "※無料版は入力されたデータを基にライン・脚質・競走得点・展開を計算します。"
)
