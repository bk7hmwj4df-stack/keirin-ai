# -*- coding: utf-8 -*-
import re
import streamlit as st
from itertools import permutations

st.set_page_config(
    page_title="🚴 競輪AIフォーメーション予想",
    page_icon="🚴",
    layout="wide"
)

# ==============================
# 見た目
# ==============================
st.title("🚴 競輪AIフォーメーション予想")
st.caption("無料版｜選手・並び・ラインから展開を分析してフォーメーションを作成")

st.info(
    "📋 使い方：出走表の画像を見ながら、下の形式で選手と並びを貼り付けるだけ。"
)

# ==============================
# 入力
# ==============================
col1, col2 = st.columns(2)

with col1:
    st.subheader("選手データ")

    default_data = """1 末迫開 102.82 両
2 幸田望夢 97.00 逃
3 長尾拳太 106.64 両
4 柿本大貴 94.32 逃
5 阪本和也 102.54 追
6 稲葉一真 92.32 追
7 橋本瑠偉 98.96 逃
8 伊藤稔真 93.00 両
9 野崎将史 97.50 両"""

    players_text = st.text_area(
        "選手データを貼り付け",
        value=default_data,
        height=330,
        help="例：1 末迫開 102.82 両"
    )

with col2:
    st.subheader("並び・ライン")

    default_line = """7-2
1-9
8-3-5
4-6"""

    lines_text = st.text_area(
        "並びを貼り付け",
        value=default_line,
        height=330,
        help="例：7-2 / 1-9 / 8-3-5 / 4-6"
    )

point_count = st.selectbox(
    "買い目点数",
    [10, 12, 14, 16, 18, 20],
    index=2
)

# ==============================
# データ解析
# ==============================
def parse_players(text):
    players = {}

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 3:
            continue

        try:
            number = int(parts[0])
        except:
            continue

        score = None
        style = ""

        for part in parts:
            try:
                value = float(part)
                if 50 <= value <= 130:
                    score = value
            except:
                pass

            if part in ["逃", "両", "追"]:
                style = part

        if score is not None:
            players[number] = {
                "number": number,
                "score": score,
                "style": style
            }

    return players


def parse_lines(text):
    result = []

    for raw in text.splitlines():
        raw = raw.strip()

        nums = [int(x) for x in re.findall(r"\d+", raw)]

        if nums:
            result.append(nums)

    return result


def get_position_scores(players, lines):
    strength = {}

    # 競走得点を基本能力として使用
    for num, p in players.items():
        strength[num] = p["score"]

    # ラインの先頭と番手に展開補正
    for line in lines:
        if not line:
            continue

        for i, num in enumerate(line):
            if num not in strength:
                continue

            if i == 0:
                strength[num] += 3.0
            elif i == 1:
                strength[num] += 2.0
            elif i == 2:
                strength[num] += 1.0

    # 逃げ選手の展開補正
    for num, p in players.items():
        if p["style"] == "逃":
            strength[num] += 1.5

        elif p["style"] == "両":
            strength[num] += 1.0

        elif p["style"] == "追":
            strength[num] += 0.5

    return strength


def make_combinations(players, lines, limit):
    strength = get_position_scores(players, lines)

    ranked = sorted(
        strength.keys(),
        key=lambda x: strength[x],
        reverse=True
    )

    # 最大6人程度までを中心に買い目作成
    main = ranked[:6]

    combinations = []

    for a, b, c in permutations(main, 3):
        score = (
            strength[a] * 0.45
            + strength[b] * 0.35
            + strength[c] * 0.20
        )

        # 同一ライン補正
        for line in lines:
            if len(line) >= 2:
                if a in line and b in line:
                    score += 2.0

                if b in line and c in line:
                    score += 1.0

        combinations.append(((a, b, c), score))

    combinations.sort(key=lambda x: x[1], reverse=True)

    selected = []
    seen = set()

    for combo, score in combinations:
        if combo not in seen:
            selected.append(combo)
            seen.add(combo)

        if len(selected) >= limit:
            break

    return selected, ranked, strength


def compress_by_first(combos):
    groups = {}

    for a, b, c in combos:
        if a not in groups:
            groups[a] = {}

        if b not in groups[a]:
            groups[a][b] = []

        groups[a][b].append(c)

    rows = []

    for a in groups:
        for b in groups[a]:
            cs = sorted(set(groups[a][b]))

            if len(cs) >= 2:
                c_text = "".join(str(x) for x in cs)
            else:
                c_text = str(cs[0])

            rows.append(f"{a}-{b}-{c_text}")

    return rows


def make_simple_formation(combos):
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
        f"{''.join(map(str, first))}-"
        f"{''.join(map(str, second))}-"
        f"{''.join(map(str, third))}"
    )


# ==============================
# 予想
# ==============================
if st.button("🔥 AIがガチ分析する", use_container_width=True):

    players = parse_players(players_text)
    lines = parse_lines(lines_text)

    if len(players) < 3:
        st.error("選手データを3人以上入力してください。")
        st.stop()

    if not lines:
        st.error("並び・ラインを入力してください。")
        st.stop()

    combos, ranked, strength = make_combinations(
        players,
        lines,
        point_count
    )

    st.success("分析完了！")

    st.divider()

    st.subheader("🎯 最終フォーメーション")

    # 細かい買い目をまとめた表示
    compact_rows = compress_by_first(combos)

    for row in compact_rows:
        st.code(row)

    st.caption(f"合計：{len(combos)}点")

    st.divider()

    st.subheader("🔥 本命評価")

    for i, num in enumerate(ranked[:5], start=1):
        score = strength[num]
        style = players[num]["style"]

        st.write(
            f"**{i}位：{num}番**　"
            f"競走得点 {players[num]['score']:.2f}　"
            f"脚質 {style}　"
            f"総合評価 {score:.1f}"
        )

    st.divider()

    st.subheader("🚴 想定展開")

    line_texts = []

    for line in lines:
        line_texts.append("-".join(map(str, line)))

    st.write(
        "ライン構成："
        + "　／　".join(line_texts)
    )

    st.write(
        "基本的には競走得点、脚質、ラインの長さと位置を総合して評価。"
    )

    st.divider()

    st.subheader("📋 買い目一覧（確認用）")

    st.code(
        "\n".join(
            f"{a}-{b}-{c}"
            for a, b, c in combos
        )
    )

    st.warning(
        "※無料版は入力データからのロジック分析です。"
        "過去レースや最新ニュースの自動取得はしません。"
    )
