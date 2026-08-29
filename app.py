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
    "出馬表の情報を貼り付けるだけで三連単フォーメーションを作成"
)

st.info(
    "📋 馬番・馬名・オッズ・人気・馬体重・増減・斤量・騎手をコピペして分析できます"
)

# ==============================
# 入力
# ==============================
col1, col2 = st.columns(2)

with col1:

    st.subheader("🏇 出走馬データ")

    default_data = """1 ロマンス 68.4 9 434 +8 55.0 石橋脩
2 オーパパ 209.7 14 486 -4 54.0 佐藤翔馬
3 ネイティヴプライド 26.0 8 482 +4 57.0 松山弘平
4 ダイヒョウカーク 125.0 10 480 -2 57.0 杉原誠人
5 プリヴィマーク 184.0 13 444 -4 57.0 武藤雅
6 ブードオブオナー 4.0 3 526 +12 57.0 津村明秀
7 ゴールドプレイヤー 3.7 2 444 +2 57.0 古川慎明
8 エターナルホープ 17.0 5 508 +8 57.0 原優介
9 オウケンサクラコ 22.2 7 414 +2 57.0 丸田恭介
10 マーゴットライス 18.0 6 480 +2 57.0 伊坂重信
11 アデルフィー 4.5 4 448 -4 57.0 三浦皇成
12 スビアソ 151.2 11 444 -8 55.0 石田拓郎
13 バターショコラ 173.7 12 458 0 55.0 小林凌也
14 ハチマン 461.4 15 466 0 54.0 水沼元輝
15 カシマライフウ 3.6 1 490 0 57.0 大野拓弥"""

    horses_text = st.text_area(
        "出馬表をコピペ",
        value=default_data,
        height=500,
        help=(
            "形式：馬番 馬名 単勝オッズ 人気 馬体重 増減 斤量 騎手\n"
            "例：1 ロマンス 68.4 9 434 +8 55.0 石橋脩"
        )
    )

with col2:

    st.subheader("🏁 レース情報")

    race_name = st.text_input(
        "レース名",
        value="未入力"
    )

    distance = st.number_input(
        "距離（m）",
        min_value=1000,
        max_value=4000,
        value=1600,
        step=100
    )

    track_type = st.selectbox(
        "コース",
        ["芝", "ダート"]
    )

    track_condition = st.selectbox(
        "馬場状態",
        ["良", "稍重", "重", "不良"]
    )

    pace = st.selectbox(
        "想定ペース",
        ["スロー", "平均", "ハイ"]
    )

    point_count = st.selectbox(
        "買い目点数",
        [10, 12, 14, 16, 18, 20],
        index=2
    )

    st.divider()

    st.subheader("⚙️ AIモード")

    mode = st.radio(
        "予想タイプ",
        [
            "🔥 本命重視",
            "⚖️ バランス",
            "💰 穴狙い"
        ],
        index=1
    )

    st.caption(
        "※オッズだけで予想を決めるのではなく、"
        "人気馬の信頼度と穴馬の期待値を分けて評価します。"
    )


# ==============================
# データ解析
# ==============================
def parse_horses(text):

    horses = {}

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        # 最低限：
        # 馬番 馬名 オッズ 人気
        if len(parts) < 4:
            continue

        try:
            number = int(parts[0])
        except:
            continue

        name = parts[1]

        # --------------------------
        # オッズ
        # --------------------------
        try:
            odds = float(
                parts[2].replace("倍", "")
            )
        except:
            odds = 999.0

        # --------------------------
        # 人気
        # --------------------------
        try:
            popularity = int(
                re.sub(
                    r"[^\d]",
                    "",
                    parts[3]
                )
            )
        except:
            popularity = 99

        # --------------------------
        # 馬体重
        # --------------------------
        weight = 0

        if len(parts) >= 5:
            try:
                weight = int(
                    re.sub(
                        r"[^\d]",
                        "",
                        parts[4]
                    )
                )
            except:
                weight = 0

        # --------------------------
        # 馬体重増減
        # --------------------------
        weight_change = 0

        if len(parts) >= 6:
            try:
                weight_change = int(
                    parts[5]
                )
            except:
                weight_change = 0

        # --------------------------
        # 斤量
        # --------------------------
        burden = 57.0

        if len(parts) >= 7:
            try:
                burden = float(
                    parts[6]
                )
            except:
                burden = 57.0

        # --------------------------
        # 騎手
        # --------------------------
        jockey = ""

        if len(parts) >= 8:
            jockey = " ".join(parts[7:])

        horses[number] = {

            "number": number,
            "name": name,
            "odds": odds,
            "popularity": popularity,
            "weight": weight,
            "weight_change": weight_change,
            "burden": burden,
            "jockey": jockey
        }

    return horses


# ==============================
# 人気評価
# ==============================
def popularity_score(popularity):

    if popularity == 1:
        return 100

    elif popularity == 2:
        return 96

    elif popularity == 3:
        return 92

    elif popularity == 4:
        return 88

    elif popularity == 5:
        return 84

    elif popularity == 6:
        return 80

    elif popularity == 7:
        return 76

    elif popularity == 8:
        return 72

    elif popularity == 9:
        return 68

    elif popularity == 10:
        return 64

    else:
        return max(
            40,
            64 - (popularity - 10) * 4
        )


# ==============================
# オッズ評価
# ==============================
def odds_score(odds):

    if odds <= 2:
        return 100

    elif odds <= 3:
        return 96

    elif odds <= 5:
        return 92

    elif odds <= 10:
        return 86

    elif odds <= 20:
        return 78

    elif odds <= 50:
        return 68

    elif odds <= 100:
        return 58

    elif odds <= 200:
        return 48

    else:
        return 40


# ==============================
# 馬体重増減評価
# ==============================
def weight_change_score(change):

    absolute_change = abs(change)

    # 大幅な馬体重変化は少し不安
    if absolute_change == 0:
        return 100

    elif absolute_change <= 4:
        return 96

    elif absolute_change <= 8:
        return 88

    elif absolute_change <= 12:
        return 76

    else:
        return 60


# ==============================
# 斤量評価
# ==============================
def burden_score(burden):

    if burden <= 54:
        return 100

    elif burden <= 55:
        return 96

    elif burden <= 56:
        return 92

    elif burden <= 57:
        return 88

    else:
        return 80


# ==============================
# 総合評価
# ==============================
def calculate_strength(horse, mode):

    pop = popularity_score(
        horse["popularity"]
    )

    odds = odds_score(
        horse["odds"]
    )

    body = weight_change_score(
        horse["weight_change"]
    )

    burden = burden_score(
        horse["burden"]
    )

    # --------------------------
    # 本命重視
    # --------------------------
    if mode == "🔥 本命重視":

        score = (
            pop * 0.55
            + odds * 0.25
            + body * 0.12
            + burden * 0.08
        )

    # --------------------------
    # バランス
    # --------------------------
    elif mode == "⚖️ バランス":

        score = (
            pop * 0.40
            + odds * 0.20
            + body * 0.25
            + burden * 0.15
        )

        # 人気薄でも馬体重が安定なら少し評価
        if horse["popularity"] >= 6:

            score += 4

        if horse["popularity"] >= 10:

            score += 3

    # --------------------------
    # 穴狙い
    # --------------------------
    else:

        score = (
            pop * 0.20
            + odds * 0.10
            + body * 0.45
            + burden * 0.25
        )

        # 穴馬補正
        if 5 <= horse["popularity"] <= 10:

            score += 10

        elif 11 <= horse["popularity"] <= 14:

            score += 7

        # 馬体重の安定を評価
        if abs(
            horse["weight_change"]
        ) <= 4:

            score += 5

    return score


# ==============================
# 1着候補スコア
# ==============================
def first_score(horse, strength):

    score = strength

    # 上位人気は勝ち切り評価
    if horse["popularity"] <= 3:
        score += 10

    elif horse["popularity"] <= 5:
        score += 5

    # 馬体重大幅変動は少し減点
    if abs(
        horse["weight_change"]
    ) >= 12:

        score -= 8

    return score


# ==============================
# 三連単作成
# ==============================
def make_combinations(
    horses,
    mode,
    pace,
    limit
):

    strength = {}

    for num, horse in horses.items():

        strength[num] = calculate_strength(
            horse,
            mode
        )

    ranked = sorted(
        strength.keys(),
        key=lambda x: strength[x],
        reverse=True
    )

    # --------------------------
    # 1着候補は上位5頭
    # --------------------------
    first_ranked = sorted(
        horses.keys(),
        key=lambda x: first_score(
            horses[x],
            strength[x]
        ),
        reverse=True
    )

    # --------------------------
    # 最大8頭を相手候補に
    # --------------------------
    main = ranked[:8]

    first_candidates = first_ranked[:4]

    combinations = []

    for a in first_candidates:

        for b, c in permutations(
            main,
            2
        ):

            # 同じ馬は不可
            if a == b or a == c:
                continue

            # ----------------------
            # 1着 50%
            # 2着 32%
            # 3着 18%
            # ----------------------
            combo_score = (
                first_score(
                    horses[a],
                    strength[a]
                ) * 0.50
                + strength[b] * 0.32
                + strength[c] * 0.18
            )

            # ======================
            # 本命馬が1着の場合
            # ======================
            if horses[a]["popularity"] <= 3:

                combo_score += 8

            # ======================
            # 中穴の2・3着
            # ======================
            if 5 <= horses[b]["popularity"] <= 10:

                combo_score += 4

            if 5 <= horses[c]["popularity"] <= 12:

                combo_score += 3

            # ======================
            # 大幅馬体重変動を減点
            # ======================
            if abs(
                horses[a]["weight_change"]
            ) >= 12:

                combo_score -= 10

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

    selected = []
    seen = set()

    # ==========================
    # 選択
    # ==========================
    for combo, score in combinations:

        if combo in seen:
            continue

        selected.append(
            combo
        )

        seen.add(
            combo
        )

        if len(selected) >= limit:
            break

    return (
        selected,
        ranked,
        strength
    )


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

            if len(cs) >= 2:

                c_text = "".join(
                    map(str, cs)
                )

            else:

                c_text = str(cs[0])

            rows.append(
                f"{a}-{b}-{c_text}"
            )

    return rows


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
            "最低3頭以上の馬データを入力してください。"
        )

        st.stop()

    combos, ranked, strength = make_combinations(
        horses,
        mode,
        pace,
        point_count
    )

    st.success(
        "🏇 分析完了！"
    )

    # ==========================
    # 最終フォーメーション
    # ==========================
    st.divider()

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

    # ==========================
    # 評価ランキング
    # ==========================
    st.divider()

    st.subheader(
        "🔥 AI総合評価"
    )

    for i, num in enumerate(
        ranked[:8],
        start=1
    ):

        horse = horses[num]

        st.write(
            f"**{i}位：{num}番 "
            f"{horse['name']}**"
        )

        st.write(
            f"単勝 {horse['odds']:.1f}倍 "
            f"({horse['popularity']}番人気)｜"
            f"馬体重 {horse['weight']}kg "
            f"({horse['weight_change']:+d})｜"
            f"斤量 {horse['burden']:.1f}kg"
        )

        st.write(
            f"騎手：{horse['jockey']}｜"
            f"AI評価：**{strength[num]:.1f}**"
        )

    # ==========================
    # 買い目一覧
    # ==========================
    st.divider()

    st.subheader(
        "📋 買い目一覧"
    )

    st.code(
        "\n".join(
            f"{a}-{b}-{c}"
            for a, b, c in combos
        )
    )

    # ==========================
    # 注意
    # ==========================
    st.warning(
        "⚠️ 現在は出馬表だけを使う簡易版です。"
        "過去戦績・調教・血統・距離適性まで追加すると"
        "さらに本格的なAIになります。"
    )
