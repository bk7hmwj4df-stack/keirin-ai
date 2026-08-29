# -*- coding: utf-8 -*-

import streamlit as st
from itertools import permutations
import re

# ==========================================
# ページ設定
# ==========================================

st.set_page_config(
    page_title="競輪AI 無料分析版",
    page_icon="🚴",
    layout="wide",
)

st.title("🚴 競輪AI 完全無料版")
st.caption(
    "API・クレジット不要。選手データとライン情報から三連単を自動分析します。"
)

# ==========================================
# 説明
# ==========================================

st.info(
    "完全無料版：OpenAI APIは使用しません。"
    "入力されたデータを点数化し、能力・近況・脚質・ライン・展開を考慮して"
    "三連単フォーメーションを作成します。"
)

# ==========================================
# レース情報
# ==========================================

st.subheader("🏁 レース情報")

col1, col2 = st.columns(2)

with col1:
    race_name = st.text_input(
        "レース名",
        placeholder="例：前橋競輪 8R",
    )

with col2:
    target_points = st.selectbox(
        "買い目点数",
        list(range(6, 21)),
        index=6,
        format_func=lambda x: f"{x}点",
    )

# ==========================================
# 選手データ
# ==========================================

st.subheader("👤 選手データ")

st.caption(
    "分かる範囲で入力してください。"
    "競走得点・直近成績・勝率などを参考に入力すると精度が上がります。"
)

riders = []

for i in range(1, 10):

    with st.expander(f"{i}番車"):

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            name = st.text_input(
                "選手名",
                key=f"name_{i}",
            )

        with c2:
            score = st.number_input(
                "競走得点",
                min_value=0.0,
                max_value=130.0,
                value=0.0,
                step=0.1,
                key=f"score_{i}",
            )

        with c3:
            form = st.slider(
                "直近の調子",
                min_value=1,
                max_value=10,
                value=5,
                key=f"form_{i}",
            )

        with c4:
            style = st.selectbox(
                "脚質",
                [
                    "追込",
                    "自在",
                    "捲り",
                    "逃げ",
                    "両方",
                ],
                key=f"style_{i}",
            )

        c5, c6, c7 = st.columns(3)

        with c5:
            self_power = st.slider(
                "自力",
                1,
                10,
                5,
                key=f"self_{i}",
            )

        with c6:
            chase_power = st.slider(
                "追込み",
                1,
                10,
                5,
                key=f"chase_{i}",
            )

        with c7:
            line_position = st.selectbox(
                "ライン内の位置",
                [
                    "単騎",
                    "先頭",
                    "番手",
                    "3番手以降",
                ],
                key=f"position_{i}",
            )

        if name.strip():
            riders.append(
                {
                    "number": i,
                    "name": name.strip(),
                    "score": score,
                    "form": form,
                    "style": style,
                    "self_power": self_power,
                    "chase_power": chase_power,
                    "position": line_position,
                }
            )

# ==========================================
# ライン入力
# ==========================================

st.subheader("🚴 ライン構成")

line_text = st.text_area(
    "並び",
    height=150,
    placeholder="""例：

7-1-6
9-5-2
8-3
4
""",
)

# ==========================================
# ライン解析
# ==========================================

def parse_lines(text):

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        nums = re.findall(r"\d+", line)

        nums = [
            int(x)
            for x in nums
            if 1 <= int(x) <= 9
        ]

        if nums:
            lines.append(nums)

    return lines


# ==========================================
# ライン評価
# ==========================================

def get_line_bonus(rider, lines):

    number = rider["number"]

    for line in lines:

        if number not in line:
            continue

        index = line.index(number)

        if index == 0:

            return {
                "first": 5,
                "second": 1,
                "third": 1,
            }

        if index == 1:

            return {
                "first": 6,
                "second": 9,
                "third": 6,
            }

        if index >= 2:

            return {
                "first": 2,
                "second": 5,
                "third": 9,
            }

    return {
        "first": 3,
        "second": 3,
        "third": 3,
    }


# ==========================================
# 各着順の評価
# ==========================================

def evaluate_rider(rider, lines):

    score_base = rider["score"]

    if score_base > 0:
        score_base = (score_base - 70) * 2
    else:
        score_base = 10

    score_base = max(0, score_base)

    form = rider["form"] * 4
    self_power = rider["self_power"] * 4
    chase_power = rider["chase_power"] * 4

    line_bonus = get_line_bonus(
        rider,
        lines,
    )

    style = rider["style"]

    first = (
        score_base
        + form
        + self_power
        + line_bonus["first"]
    )

    second = (
        score_base
        + form
        + (self_power * 0.6)
        + chase_power
        + line_bonus["second"]
    )

    third = (
        score_base
        + form
        + (self_power * 0.4)
        + (chase_power * 1.2)
        + line_bonus["third"]
    )

    if style == "逃げ":

        first += 8

        second += 2

    elif style == "捲り":

        first += 7

        second += 4

    elif style == "自在":

        first += 5

        second += 6

        third += 4

    elif style == "追込":

        first += 2

        second += 8

        third += 10

    elif style == "両方":

        first += 6

        second += 5

        third += 4

    return {
        "first": first,
        "second": second,
        "third": third,
    }


# ==========================================
# 組み合わせ評価
# ==========================================

def combination_score(a, b, c, evaluations):

    return (
        evaluations[a]["first"]
        + evaluations[b]["second"]
        + evaluations[c]["third"]
    )


# ==========================================
# フォーメーション変換
# ==========================================

def make_formation(combos):

    if not combos:
        return []

    remaining = combos.copy()

    formations = []

    while remaining:

        a = remaining[0][0]

        same_first = [
            x for x in remaining
            if x[0] == a
        ]

        second_numbers = sorted(
            set(
                x[1]
                for x in same_first
            )
        )

        third_numbers = sorted(
            set(
                x[2]
                for x in same_first
            )
        )

        second_text = "".join(
            str(x)
            for x in second_numbers
        )

        third_text = "".join(
            str(x)
            for x in third_numbers
        )

        formation = (
            f"{a}-{second_text}-{third_text}"
        )

        formations.append(formation)

        for x in same_first:
            if x in remaining:
                remaining.remove(x)

    return formations


# ==========================================
# 分析
# ==========================================

if st.button(
    "🔥 無料AIが分析する",
    type="primary",
    use_container_width=True,
):

    if len(riders) < 3:

        st.error(
            "最低3人以上の選手を入力してください。"
        )

        st.stop()

    lines = parse_lines(line_text)

    evaluations = {}

    for rider in riders:

        number = rider["number"]

        evaluations[number] = evaluate_rider(
            rider,
            lines,
        )

    # ------------------------------------------
    # 全組み合わせ
    # ------------------------------------------

    numbers = [
        rider["number"]
        for rider in riders
    ]

    combos = []

    for combo in permutations(
        numbers,
        3,
    ):

        score = combination_score(
            combo[0],
            combo[1],
            combo[2],
            evaluations,
        )

        combos.append(
            {
                "combo": combo,
                "score": score,
            }
        )

    # ------------------------------------------
    # 並び替え
    # ------------------------------------------

    combos = sorted(
        combos,
        key=lambda x: x["score"],
        reverse=True,
    )

    # ------------------------------------------
    # 1着固定しすぎ防止
    # ------------------------------------------

    selected = []

    first_counts = {}

    for item in combos:

        combo = item["combo"]

        first = combo[0]

        if first_counts.get(first, 0) >= max(
            2,
            target_points // 2,
        ):
            continue

        selected.append(item)

        first_counts[first] = (
            first_counts.get(first, 0) + 1
        )

        if len(selected) >= target_points:
            break

    # ------------------------------------------
    # 足りない場合
    # ------------------------------------------

    if len(selected) < target_points:

        used = set(
            item["combo"]
            for item in selected
        )

        for item in combos:

            if item["combo"] in used:
                continue

            selected.append(item)

            if len(selected) >= target_points:
                break

    # ------------------------------------------
    # 印
    # ------------------------------------------

    total_rank = []

    for rider in riders:

        n = rider["number"]

        total = (
            evaluations[n]["first"]
            + evaluations[n]["second"]
            + evaluations[n]["third"]
        )

        total_rank.append(
            (
                n,
                total,
                rider["name"],
            )
        )

    total_rank.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    # ------------------------------------------
    # 結果
    # ------------------------------------------

    st.divider()

    st.subheader("🤖 無料AI分析結果")

    if len(total_rank) >= 1:

        st.write(
            f"◎ 本命：{total_rank[0][0]}番 "
            f"{total_rank[0][2]}"
        )

    if len(total_rank) >= 2:

        st.write(
            f"○ 対抗：{total_rank[1][0]}番 "
            f"{total_rank[1][2]}"
        )

    if len(total_rank) >= 3:

        st.write(
            f"▲ 単穴：{total_rank[2][0]}番 "
            f"{total_rank[2][2]}"
        )

    if len(total_rank) >= 4:

        st.write(
            f"☆ 穴：{total_rank[3][0]}番 "
            f"{total_rank[3][2]}"
        )

    # ------------------------------------------
    # 展開
    # ------------------------------------------

    st.subheader("🏁 想定展開")

    if lines:

        for line in lines:

            line_display = "-".join(
                str(x)
                for x in line
            )

            st.write(
                f"ライン：{line_display}"
            )

    else:

        st.write(
            "ライン情報が未入力のため、"
            "個人データ中心で分析しました。"
        )

    # ------------------------------------------
    # 最終買い目
    # ------------------------------------------

    st.subheader("🎯 最終フォーメーション")

    final_combos = [
        item["combo"]
        for item in selected
    ]

    for combo in final_combos:

        st.write(
            f"{combo[0]}-{combo[1]}-{combo[2]}"
        )

    st.success(
        f"合計：{len(final_combos)}点"
    )

    # ------------------------------------------
    # コピペ用
    # ------------------------------------------

    st.subheader("📋 コピペ用")

    copy_text = "\n".join(
        f"{combo[0]}-{combo[1]}-{combo[2]}"
        for combo in final_combos
    )

    st.code(
        copy_text,
        language=None,
    )

# ==========================================
# 注意
# ==========================================

st.divider()

st.caption(
    "※完全無料版です。OpenAI APIは使用しません。"
    "入力データを数値化して予想する補助ツールであり、的中を保証するものではありません。"
)
