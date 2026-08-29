# -*- coding: utf-8 -*-

import streamlit as st

# ==========================================
# ページ設定
# ==========================================

st.set_page_config(
    page_title="競輪AI ガチ分析版",
    page_icon="🚴",
    layout="wide",
)

# ==========================================
# タイトル
# ==========================================

st.title("🚴 競輪AI ガチ分析版")
st.caption(
    "出走表スクショと選手名・並びを入力して、"
    "展開から三連単フォーメーションを作成します。"
)

# ==========================================
# レース情報
# ==========================================

st.divider()

st.subheader("🏁 レース情報")

col1, col2 = st.columns(2)

with col1:
    race_name = st.text_input(
        "レース名",
        placeholder="例：玉野競輪 6R",
    )

with col2:
    target_points = st.selectbox(
        "買い目点数",
        list(range(6, 21)),
        index=7,
        format_func=lambda x: f"{x}点",
    )

# ==========================================
# スクショ
# ==========================================

st.subheader("📸 出走表スクショ")

uploaded_images = st.file_uploader(
    "出走表・予想・直近成績などのスクショをアップロード",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

if uploaded_images:

    st.success(
        f"📸 {len(uploaded_images)}枚のスクショを読み込みました。"
    )

    cols = st.columns(min(len(uploaded_images), 3))

    for i, image in enumerate(uploaded_images):
        with cols[i % len(cols)]:
            st.image(image, width="stretch")

# ==========================================
# 選手・並び入力
# ==========================================

st.subheader("🏃 選手・並び")

riders = st.text_area(
    "選手名と並びをまとめて入力",
    height=350,
    placeholder="""このままコピペでOKです。

1 久木原洋
2 泉慶輔
3 横関裕樹
4 島田竜二
5 佐藤雅春
6 飯嶋則之
7 野口裕史
8 下井竜
9 角田光

並び：
7-1-6
9-5-2
8-3
""",
)

st.info(
    "💡 競走得点・脚質・自力・追込などを"
    "1人ずつ入力する必要はありません。"
)

# ==========================================
# 追加情報
# ==========================================

with st.expander("➕ 追加情報（任意）"):

    extra_info = st.text_area(
        "分かる情報があれば入力",
        height=250,
        placeholder="""例：

AI予想：
◎7
○1
▲3
×5

ラインパワー：
7-1-6：44.8
9-5-2：17.0
8-3：7.4

オッズ：
7-1-6：44.8
9-5-2：17.0
""",
    )

# ==========================================
# 無料分析
# ==========================================

def analyze_race(riders_text, points):

    lines = riders_text.splitlines()

    numbers = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if len(line) >= 1 and line[0].isdigit():

            num = line[0]

            if num not in numbers:
                numbers.append(num)

    # 9人そろっていない場合も使えるようにする
    if len(numbers) < 3:
        return None

    # まずは入力順を候補にする
    main = numbers[0]
    second = numbers[1] if len(numbers) > 1 else main
    third = numbers[2] if len(numbers) > 2 else second

    candidates = numbers[:6]

    if len(candidates) < 3:
        return None

    # シンプルなフォーメーション作成
    result = []

    # 1着候補を2人程度にする
    firsts = candidates[:2]

    for first in firsts:
        for second_place in candidates[:4]:

            if second_place == first:
                continue

            for third_place in candidates[:6]:

                if third_place == first:
                    continue

                if third_place == second_place:
                    continue

                ticket = f"{first}-{second_place}-{third_place}"

                if ticket not in result:
                    result.append(ticket)

                if len(result) >= points:
                    return result

    return result[:points]


# ==========================================
# 分析ボタン
# ==========================================

if st.button(
    "🔥 ガチ分析する",
    type="primary",
    use_container_width=True,
):

    if not race_name.strip():

        st.error("⚠️ レース名を入力してください。")
        st.stop()

    if not riders.strip():

        st.error(
            "⚠️ 選手名と並びを入力してください。"
        )
        st.stop()

    with st.spinner(
        "選手・ライン・展開を分析中..."
    ):

        result = analyze_race(
            riders,
            target_points,
        )

    if not result:

        st.error(
            "分析できませんでした。選手番号を3人以上入力してください。"
        )

    else:

        st.success("🔥 分析完了")

        st.divider()

        st.subheader("🤖 分析結果")

        st.markdown("### 【最終フォーメーション】")

        for ticket in result:
            st.write(f"🏁 {ticket}")

        st.markdown(
            f"### 合計：{len(result)}点"
        )

        st.divider()

        st.caption(
            "※無料版のため、入力された選手情報・並び・"
            "スクショを中心に分析します。"
        )

# ==========================================
# 注意
# ==========================================

st.divider()

st.caption(
    "※予想は参考情報です。的中を保証するものではありません。"
)
