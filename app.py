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
st.caption(
    "無料版｜本線だけでなく、ライン崩れ・先行争いまで想定してフォーメーションを作成"
)

st.info(
    """
📋 入力した選手データと並びから複数の展開を想定します。

① 本線：ラインが普通に機能
② 中穴：別ラインの早仕掛け・捲り
③ 穴：先行争い・ライン崩れ・番手離れ

穴を適当に増やすのではなく、
「なぜその選手が浮上するか」を展開から評価します。
"""
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
    [6, 8, 10, 12, 14, 16, 18, 20],
    index=4
)

# ==============================
# 選手データ解析
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


# ==============================
# ライン解析
# ==============================
def parse_lines(text):
    result = []

    for raw in text.splitlines():
        raw = raw.strip()

        nums = [int(x) for x in re.findall(r"\d+", raw)]

        if nums:
            result.append(nums)

    return result


# ==============================
# ライン位置取得
# ==============================
def get_line_info(players, lines):
    info = {}

    for line_index, line in enumerate(lines):
        for position, num in enumerate(line):
            info[num] = {
                "line": line_index,
                "position": position,
                "line_length": len(line)
            }

    return info


# ==============================
# 基礎能力評価
# ==============================
def get_base_strength(players, lines):
    strength = {}

    for num, p in players.items():
        value = p["score"]

        # 脚質補正
        if p["style"] == "逃":
            value += 1.5

        elif p["style"] == "両":
            value += 1.0

        elif p["style"] == "追":
            value += 0.5

        strength[num] = value

    return strength


# ==============================
# 本線展開
# ラインが普通に機能する
# ==============================
def get_main_strength(players, lines):
    strength = get_base_strength(players, lines)

    for line in lines:
        if not line:
            continue

        for position, num in enumerate(line):
            if num not in strength:
                continue

            # 先頭
            if position == 0:
                strength[num] += 3.0

                if players[num]["style"] in ["逃", "両"]:
                    strength[num] += 2.0

            # 番手
            elif position == 1:
                strength[num] += 3.5

            # 3番手以降
            else:
                strength[num] += 1.5

        # 長いライン補正
        if len(line) >= 3:
            for num in line:
                if num in strength:
                    strength[num] += 1.0

    return strength


# ==============================
# 中穴展開
# 別線の早仕掛け・捲り
# ==============================
def get_middle_strength(players, lines):
    strength = get_base_strength(players, lines)

    for line in lines:
        if not line:
            continue

        for position, num in enumerate(line):
            if num not in strength:
                continue

            style = players[num]["style"]

            # 先頭の自力型を強化
            if position == 0:

                if style == "逃":
                    strength[num] += 4.0

                elif style == "両":
                    strength[num] += 4.5

            # 番手も残る可能性
            elif position == 1:
                strength[num] += 2.5

    return strength


# ==============================
# 穴展開
# ラインが乱れる・先行争い
# ==============================
def get_chaos_strength(players, lines):
    strength = get_base_strength(players, lines)

    info = get_line_info(players, lines)

    # 自力選手の人数
    attackers = []

    for num, p in players.items():
        if p["style"] in ["逃", "両"]:
            line_info = info.get(num)

            if line_info and line_info["position"] == 0:
                attackers.append(num)

    many_attackers = len(attackers) >= 3

    for num, p in players.items():

        line_info = info.get(num)

        if not line_info:
            continue

        position = line_info["position"]
        line_length = line_info["line_length"]
        style = p["style"]

        # 先行争いなら後ろが浮上
        if many_attackers:

            if position == 1:
                strength[num] += 5.0

            elif position >= 2:
                strength[num] += 3.5

        # 単騎・短いラインの自力型
        if line_length <= 2:

            if position == 0 and style == "両":
                strength[num] += 4.0

            elif position == 0 and style == "逃":
                strength[num] += 2.0

        # 追込み型の展開拾い
        if style == "追":

            if position == 1:
                strength[num] += 2.0

            elif position >= 2:
                strength[num] += 3.0

    return strength


# ==============================
# 三連単候補作成
# ==============================
def generate_scenario_combos(
    players,
    lines,
    strength,
    scenario,
    top_count=7
):
    ranked = sorted(
        strength.keys(),
        key=lambda x: strength[x],
        reverse=True
    )

    main = ranked[:top_count]

    combos = []

    for a, b, c in permutations(main, 3):

        score = (
            strength[a] * 0.48
            + strength[b] * 0.32
            + strength[c] * 0.20
        )

        # --------------------------
        # ライン関係
        # --------------------------
        for line in lines:

            if len(line) < 2:
                continue

            # 同一ラインの順当決着
            if scenario == "main":

                if a in line and b in line:
                    if line.index(a) < line.index(b):
                        score += 2.5

                if b in line and c in line:
                    if line.index(b) < line.index(c):
                        score += 1.5

            # 中穴：自力選手からの捲り
            elif scenario == "middle":

                if a in line and players[a]["style"] in ["逃", "両"]:
                    if line.index(a) == 0:
                        score += 2.5

                if a in line and b in line:
                    score += 1.0

            # 穴：ライン崩れ
            elif scenario == "chaos":

                # 1着と2着を同一ライン固定にしすぎない
                if a in line and b in line:
                    score += 0.3

                # 番手・3番手の浮上
                if b in line and line.index(b) >= 1:
                    score += 1.8

                if c in line and line.index(c) >= 1:
                    score += 1.2

        combos.append({
            "ticket": (a, b, c),
            "score": score,
            "scenario": scenario
        })

    combos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return combos


# ==============================
# 最終買い目作成
# ==============================
def make_final_combinations(players, lines, limit):

    main_strength = get_main_strength(players, lines)
    middle_strength = get_middle_strength(players, lines)
    chaos_strength = get_chaos_strength(players, lines)

    main_combos = generate_scenario_combos(
        players,
        lines,
        main_strength,
        "main"
    )

    middle_combos = generate_scenario_combos(
        players,
        lines,
        middle_strength,
        "middle"
    )

    chaos_combos = generate_scenario_combos(
        players,
        lines,
        chaos_strength,
        "chaos"
    )

    # --------------------------
    # 点数配分
    # --------------------------
    main_count = max(3, round(limit * 0.55))
    middle_count = max(2, round(limit * 0.30))
    chaos_count = max(1, limit - main_count - middle_count)

    selected = []
    seen = set()

    # 本線
    for item in main_combos:
        if len([x for x in selected if x["scenario"] == "main"]) >= main_count:
            break

        ticket = item["ticket"]

        if ticket not in seen:
            selected.append(item)
            seen.add(ticket)

    # 中穴
    for item in middle_combos:
        if len([x for x in selected if x["scenario"] == "middle"]) >= middle_count:
            break

        ticket = item["ticket"]

        if ticket not in seen:
            selected.append(item)
            seen.add(ticket)

    # 穴
    for item in chaos_combos:
        if len([x for x in selected if x["scenario"] == "chaos"]) >= chaos_count:
            break

        ticket = item["ticket"]

        if ticket not in seen:
            selected.append(item)
            seen.add(ticket)

    # 足りない場合
    all_combos = (
        main_combos
        + middle_combos
        + chaos_combos
    )

    all_combos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    for item in all_combos:
        if len(selected) >= limit:
            break

        ticket = item["ticket"]

        if ticket not in seen:
            selected.append(item)
            seen.add(ticket)

    # 多すぎる場合
    selected = selected[:limit]

    return (
        selected,
        main_strength,
        middle_strength,
        chaos_strength
    )


# ==============================
# フォーメーション圧縮
# ==============================
def compress_tickets(items):

    groups = {}

    for item in items:
        a, b, c = item["ticket"]

        if a not in groups:
            groups[a] = {}

        if b not in groups[a]:
            groups[a][b] = []

        groups[a][b].append(c)

    rows = []

    for a in groups:

        for b in groups[a]:

            thirds = sorted(
                set(groups[a][b])
            )

            third_text = "".join(
                str(x) for x in thirds
            )

            rows.append(
                f"{a}-{b}-{third_text}"
            )

    return rows


# ==============================
# シナリオ名
# ==============================
def scenario_name(scenario):

    if scenario == "main":
        return "本線"

    if scenario == "middle":
        return "中穴"

    if scenario == "chaos":
        return "穴・ライン崩れ"

    return scenario


# ==============================
# 予想
# ==============================
if st.button(
    "🔥 AIがガチ分析する",
    use_container_width=True,
    type="primary"
):

    players = parse_players(players_text)
    lines = parse_lines(lines_text)

    if len(players) < 3:
        st.error(
            "選手データを3人以上入力してください。"
        )
        st.stop()

    if not lines:
        st.error(
            "並び・ラインを入力してください。"
        )
        st.stop()

    (
        selected,
        main_strength,
        middle_strength,
        chaos_strength
    ) = make_final_combinations(
        players,
        lines,
        point_count
    )

    # ==========================
    # 総合ランキング
    # ==========================
    total_strength = {}

    for num in players:
        total_strength[num] = (
            main_strength[num] * 0.55
            + middle_strength[num] * 0.25
            + chaos_strength[num] * 0.20
        )

    ranked = sorted(
        players.keys(),
        key=lambda x: total_strength[x],
        reverse=True
    )

    # ==========================
    # 表示
    # ==========================
    st.success("分析完了！")

    st.divider()

    st.header("🎯 AI結論")

    labels = ["◎", "○", "▲", "☆"]

    cols = st.columns(4)

    for i, num in enumerate(ranked[:4]):

        with cols[i]:
            st.metric(
                labels[i],
                f"{num}番",
                f"{players[num]['score']:.2f}点"
            )

    st.divider()

    # ==========================
    # 展開分析
    # ==========================
    st.subheader("🚴 想定展開")

    line_texts = [
        "-".join(map(str, line))
        for line in lines
    ]

    st.write(
        "ライン構成："
        + " ／ ".join(line_texts)
    )

    st.write(
        "① **本線展開**：有力ラインが主導権を取って番手・ライン選手が残る。"
    )

    st.write(
        "② **中穴展開**：別線の自力選手が早めに仕掛け、捲りや逆転が発生。"
    )

    st.write(
        "③ **穴展開**：複数ラインの先行争いで隊列が乱れ、番手・3番手・別線が浮上。"
    )

    # ==========================
    # 穴候補
    # ==========================
    chaos_rank = sorted(
        players.keys(),
        key=lambda x: chaos_strength[x],
        reverse=True
    )

    st.subheader("💥 ライン崩れ時の穴候補")

    hole_candidates = chaos_rank[:4]

    st.write(
        " → ".join(
            f"{num}番"
            for num in hole_candidates
        )
    )

    st.caption(
        "通常展開ではなく、先行争い・番手離れ・隊列の乱れが起きた場合に評価が上がる候補です。"
    )

    # ==========================
    # 最終フォーメーション
    # ==========================
    st.divider()

    st.header("🎯 最終フォーメーション")

    compact_rows = compress_tickets(selected)

    for row in compact_rows:
        st.code(row)

    st.success(
        f"合計：{len(selected)}点"
    )

    # ==========================
    # シナリオ別
    # ==========================
    with st.expander("シナリオ別の買い目を見る"):

        for scenario in ["main", "middle", "chaos"]:

            scenario_items = [
                x for x in selected
                if x["scenario"] == scenario
            ]

            if scenario_items:

                st.subheader(
                    f"【{scenario_name(scenario)}】"
                )

                for item in scenario_items:

                    a, b, c = item["ticket"]

                    st.write(
                        f"{a}-{b}-{c}"
                    )

    # ==========================
    # 選手評価
    # ==========================
    with st.expander("全選手の総合評価を見る"):

        for i, num in enumerate(
            ranked,
            start=1
        ):

            st.write(
                f"{i}位："
                f"{num}番 "
                f"得点 {players[num]['score']:.2f} "
                f"脚質 {players[num]['style']} "
                f"総合評価 {total_strength[num]:.1f}"
            )

    # ==========================
    # 買い目確認
    # ==========================
    with st.expander("実際の全買い目を確認"):

        for item in selected:

            a, b, c = item["ticket"]

            st.write(
                f"{a}-{b}-{c}"
                f"（{scenario_name(item['scenario'])}）"
            )

    st.warning(
        "※無料版は入力された競走得点・脚質・ライン構成から展開をシミュレーションするロジックです。"
    )
