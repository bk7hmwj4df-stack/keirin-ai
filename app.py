# -*- coding: utf-8 -*-
import re
import streamlit as st
from itertools import permutations

# ==============================
# 基本設定
# ==============================
st.set_page_config(
    page_title="🏇 競馬AIフォーメーション予想",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 競馬AIフォーメーション予想")
st.caption(
    "過去成績・持ち時計・調教・適性・騎手・展開を総合分析して三連単を作成"
)

st.info(
    "📋 馬データを下の形式で貼り付けて分析します。"
)

# ==============================
# 入力
# ==============================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏇 馬データ")

    default_data = """1 サンプル馬A 90 88 85 90 80 88
2 サンプル馬B 95 92 80 85 88 92
3 サンプル馬C 82 85 95 88 90 80
4 サンプル馬D 88 90 90 82 85 85
5 サンプル馬E 80 78 88 92 82 90
6 サンプル馬F 85 87 82 80 95 88"""

    horses_text = st.text_area(
        "馬データを貼り付け",
        value=default_data,
        height=360,
        help=(
            "形式：馬番 馬名 過去成績 持ち時計 調教 適性 騎手 展開\n"
            "例：1 イクイノックス 95 98 92 96 95 90"
        )
    )

with col2:
    st.subheader("⚙️ レース条件")

    distance = st.number_input(
        "距離（m）",
        min_value=1000,
        max_value=4000,
        value=1600,
        step=100
    )

    track_type = st.selectbox(
        "コース",
        ["芝", "ダート", "障害"]
    )

    pace = st.selectbox(
        "想定ペース",
        ["スロー", "平均", "ハイ"]
    )

    point_count = st.selectbox(
        "買い目点数",
        [10, 12, 14, 16, 18, 20, 24],
        index=2
    )

    st.markdown("### 🏇 展開評価")

    st.caption(
        "展開は馬データの最後の数字で評価します。"
    )

    st.caption(
        "スロー＝差し・追い込み不利、先行有利"
    )

    st.caption(
        "ハイ＝逃げ・先行不利、差し有利"
    )

# ==============================
# 馬データ解析
# ==============================
def parse_horses(text):

    horses = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 8:
            continue

        try:
            number = int(parts[0])
        except:
            continue

        name = parts[1]

        values = []

        for part in parts[2:]:
            try:
                values.append(float(part))
            except:
                pass

        if len(values) >= 6:

            horses[number] = {
                "number": number,
                "name": name,

                "past": values[0],
                "time": values[1],
                "training": values[2],
                "aptitude": values[3],
                "jockey": values[4],
                "pace": values[5]
            }

    return horses


# ==============================
# 総合評価
# ==============================
def calculate_strength(horse):

    # --------------------------
    # かぁち仕様の評価順
    #
    # ① 過去戦績
    # ② 持ち時計
    # ③ 調教
    # ④ 距離・コース適性
    # ⑤ 騎手
    # ⑥ 展開
    #
    # オッズは使わない
    # --------------------------

    score = (
        horse["past"] * 0.25
        + horse["time"] * 0.20
        + horse["training"] * 0.18
        + horse["aptitude"] * 0.15
        + horse["jockey"] * 0.12
        + horse["pace"] * 0.10
    )

    return score


# ==============================
# 展開補正
# ==============================
def apply_pace_bonus(horses, pace):

    result = {}

    for num, horse in horses.items():

        strength = calculate_strength(horse)

        pace_score = horse["pace"]

        # ----------------------
        # ハイペース
        # 差し・追込評価が高い馬を優遇
        # ----------------------
        if pace == "ハイ":

            if pace_score >= 90:
                strength += 4.0

            elif pace_score >= 80:
                strength += 2.0

            elif pace_score < 60:
                strength -= 2.0

        # ----------------------
        # スローペース
        # 前に行ける馬を優遇
        # ----------------------
        elif pace == "スロー":

            if pace_score >= 85:
                strength += 2.0

            elif pace_score < 60:
                strength -= 1.5

        # ----------------------
        # 平均ペース
        # 基本能力重視
        # ----------------------
        else:

            if pace_score >= 85:
                strength += 1.0

        result[num] = strength

    return result


# ==============================
# 三連単スコア
# ==============================
def make_combinations(
    horses,
    pace,
    limit
):

    strength = apply_pace_bonus(
        horses,
        pace
    )

    ranked = sorted(
        strength.keys(),
        key=lambda x: strength[x],
        reverse=True
    )

    # 上位6頭を中心にする
    main = ranked[:6]

    combinations = []

    for a, b, c in permutations(main, 3):

        # ----------------------
        # 1着
        # ----------------------
        score_a = (
            strength[a] * 0.50
        )

        # ----------------------
        # 2着
        # ----------------------
        score_b = (
            strength[b] * 0.32
        )

        # ----------------------
        # 3着
        # ----------------------
        score_c = (
            strength[c] * 0.18
        )

        combo_score = (
            score_a
            + score_b
            + score_c
        )

        # ======================
        # 1着能力を重視
        # ======================

        # 過去戦績
        combo_score += (
            horses[a]["past"] * 0.10
        )

        # 持ち時計
        combo_score += (
            horses[a]["time"] * 0.08
        )

        # 調教
        combo_score += (
            horses[a]["training"] * 0.07
        )

        # ======================
        # 2・3着は能力差を許容
        # ======================

        combo_score += (
            horses[b]["past"] * 0.04
        )

        combo_score += (
            horses[c]["past"] * 0.02
        )

        combinations.append(
            (
                (a, b, c),
                combo_score
            )
        )

    combinations.sort(
        key=lambda x: x[1],
        reverse=True
    )

    # ==========================
    # 上位から選択
    # ==========================
    selected = []

    for combo, score in combinations:

        if combo not in selected:
            selected.append(combo)

        if len(selected) >= limit:
            break

    return selected, ranked, strength


# ==============================
# フォーメーション圧縮
# ==============================
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

            cs = sorted(
                set(groups[a][b])
            )

            c_text = "".join(
                str(x)
                for x in cs
            )

            rows.append(
                f"{a}-{b}-{c_text}"
            )

    return rows


# ==============================
# 普通のフォーメーション作成
# ==============================
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
        f"{''.join(map(str, first))}"
        f"-"
        f"{''.join(map(str, second))}"
        f"-"
        f"{''.join(map(str, third))}"
    )


# ==============================
# AI分析
# ==============================
if st.button(
    "🔥 AIがガチ分析する",
    use_container_width=True
):

    horses = parse_horses(
        horses_text
    )

    if len(horses) < 3:

        st.error(
            "馬データを3頭以上入力してください。"
        )

        st.stop()

    # ==========================
    # 分析開始
    # ==========================
    combos, ranked, strength = make_combinations(
        horses,
        pace,
        point_count
    )

    st.success(
        "🏇 分析完了！"
    )

    st.divider()

    # ==========================
    # 最終フォーメーション
    # ==========================
    st.subheader(
        "🎯 最終フォーメーション"
    )

    compact_rows = compress_by_first(
        combos
    )

    for row in compact_rows:

        st.code(
            row
        )

    st.caption(
        f"合計：{len(combos)}点"
    )

    st.divider()

    # ==========================
    # 本命評価
    # ==========================
    st.subheader(
        "🔥 総合評価"
    )

    for i, num in enumerate(
        ranked,
        start=1
    ):

        if i > 6:
            break

        horse = horses[num]

        st.write(
            f"**{i}位：{num}番 "
            f"{horse['name']}**"
        )

        st.write(
            f"過去成績 {horse['past']:.0f}｜"
            f"持ち時計 {horse['time']:.0f}｜"
            f"調教 {horse['training']:.0f}｜"
            f"適性 {horse['aptitude']:.0f}｜"
            f"騎手 {horse['jockey']:.0f}｜"
            f"展開 {horse['pace']:.0f}"
        )

        st.write(
            f"総合評価：**{strength[num]:.1f}**"
        )

    st.divider()

    # ==========================
    # 想定展開
    # ==========================
    st.subheader(
        "🏇 想定展開"
    )

    st.write(
        f"距離：{distance}m"
    )

    st.write(
        f"コース：{track_type}"
    )

    st.write(
        f"想定ペース：{pace}"
    )

    if pace == "ハイ":

        st.write(
            "前半から速くなり、"
            "差し・追い込み評価が高い馬を優遇。"
        )

    elif pace == "スロー":

        st.write(
            "前半が落ち着き、"
            "前に行ける馬を優遇。"
        )

    else:

        st.write(
            "能力比較を中心に評価。"
        )

    st.divider()

    # ==========================
    # 買い目一覧
    # ==========================
    st.subheader(
        "📋 買い目一覧（確認用）"
    )

    st.code(
        "\n".join(
            f"{a}-{b}-{c}"
            for a, b, c in combos
        )
    )

    st.warning(
        "※オッズを予想の順位決定には使用しません。"
        "オッズは買い目の厚さや期待値確認に使う前提です。"
    )
