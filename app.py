# -*- coding: utf-8 -*-

import os
import base64
import streamlit as st
from openai import OpenAI

# ==========================================
# ページ設定
# ==========================================

st.set_page_config(
    page_title="競輪AI ガチ分析版",
    page_icon="🚴",
    layout="wide",
)

st.title("🚴 競輪AI ガチ分析版")
st.caption(
    "AIが過去成績・近況・脚質・ライン・展開を分析し、"
    "三連単フォーメーションを作成します。"
)

# ==========================================
# APIキー取得
# ==========================================

api_key = ""

try:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
except Exception:
    pass

if not api_key:
    api_key = os.getenv("OPENAI_API_KEY", "")

# 文字列化・空白除去
api_key = str(api_key).strip().replace("\n", "").replace("\r", "")

if not api_key:
    st.error("OPENAI_API_KEY が設定されていません。")
    st.stop()

# APIキーに日本語などが混入していないか確認
try:
    api_key.encode("ascii")
except UnicodeEncodeError:
    st.error(
        "OPENAI_API_KEY に日本語または特殊文字が混ざっています。"
    )
    st.info(
        "Streamlit SecretsのAPIキーを削除して、"
        "OpenAIのAPIキーだけを貼り直してください。"
    )
    st.stop()

if not api_key.startswith("sk-"):
    st.error(
        "OPENAI_API_KEY の形式が正しくない可能性があります。"
    )
    st.info(
        "sk- から始まるOpenAI APIキーだけを設定してください。"
    )
    st.stop()

# OpenAIクライアント
client = OpenAI(
    api_key=api_key,
    timeout=120.0,
    max_retries=2,
)

# ==========================================
# AIへの指示
# ==========================================

SYSTEM_PROMPT = """
あなたは競輪の三連単予想を専門にする高度な競輪分析AIです。

単純な競走得点順や人気順ではなく、
可能な限りWeb検索を使って実際の選手データ、
過去成績、近況、脚質、ライン、展開を分析してください。

【必ず確認すること】

・過去成績
・直近成績
・競走得点
・決まり手
・S、H、B
・脚質
・先行力
・捲り力
・追込み能力
・番手戦の強さ
・直近の調子
・ライン構成
・並び
・主導権争い
・バンク特性

【最重要ルール】

1. 最初にオッズで予想を決めない。
2. まず選手能力と展開で評価する。
3. オッズは最後の参考にする。
4. 存在しないデータを作らない。
5. 分からない情報を事実のように書かない。
6. 既存AI予想をそのままコピーしない。
7. 独自に全選手を評価する。

【分析手順】

STEP1
全選手を評価する。

STEP2
ライン構成を分析する。

STEP3
最低3パターンの展開を考える。

A：本命ラインが主導権
B：別線の捲り
C：先行争いから番手や追込みが浮上

STEP4
1着、2着、3着を別々に評価する。

【フォーメーション】

明確な1強でない限り、
1着候補は原則2人程度。

1着と2着を固定した買い方を
何度も繰り返さない。

例えば、

1-2-345
1-2-367

のような、
同じ1着2着固定の重複を避ける。

展開に応じて、

1着候補
2着候補
3着候補

を自然に入れ替える。

変則的すぎるフォーメーションは避ける。

【点数】

ユーザー指定の最大点数を絶対に超えない。

必ず三連単を実際に展開し、
重複を除いた最終点数を確認する。

【出力】

【AI結論】
◎ 本命
○ 対抗
▲ 単穴
☆ 穴

【想定展開】

短く説明。

【最終フォーメーション】

最後に見やすい形式で買い目を出す。

例：

7-13-12356
1-7-12356

合計：10点

説明より買い目精度を最優先する。
"""

# ==========================================
# レース情報
# ==========================================

st.divider()
st.subheader("🏁 レース情報")

col1, col2 = st.columns(2)

with col1:
    race_name = st.text_input(
        "レース名",
        placeholder="例：高松競輪 5R",
    )

with col2:
    target_points = st.selectbox(
        "買い目点数",
        list(range(6, 21)),
        index=6,
        format_func=lambda x: f"{x}点",
    )

# ==========================================
# スクショ
# ==========================================

st.subheader("📸 出走表スクショ（任意）")

uploaded_images = st.file_uploader(
    "出走表・予想・直近成績などのスクショ",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

if uploaded_images:
    st.success(
        f"{len(uploaded_images)}枚の画像を読み込みました。"
    )

# ==========================================
# テキスト入力
# ==========================================

riders = st.text_area(
    "出走選手・並び情報",
    height=300,
    placeholder="""例：

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

extra_info = st.text_area(
    "追加情報（任意）",
    height=200,
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
""",
)

st.caption(
    "スクショだけでも分析できます。"
    "選手名や並びも入力すると精度が上がります。"
)

# ==========================================
# 画像変換
# ==========================================

def make_image_content(uploaded_file):

    image_bytes = uploaded_file.getvalue()

    mime_type = uploaded_file.type

    if not mime_type:
        mime_type = "image/jpeg"

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("ascii")

    return {
        "type": "input_image",
        "image_url": (
            f"data:{mime_type};base64,"
            f"{image_base64}"
        ),
    }

# ==========================================
# 分析実行
# ==========================================

if st.button(
    "🔥 AIがガチ分析する",
    type="primary",
    use_container_width=True,
):

    if not race_name.strip():
        st.error("レース名を入力してください。")
        st.stop()

    if not riders.strip() and not uploaded_images:
        st.error(
            "出走選手情報を入力するか、"
            "スクショをアップロードしてください。"
        )
        st.stop()

    point_instruction = f"""
最終買い目は最大{target_points}点まで。

絶対に{target_points}点を超えない。

できるだけ{target_points}点に近づける。

最終出力前に実際の三連単を展開し、
重複を除いて点数を再計算すること。
"""

    user_text = f"""
以下の競輪レースを本気で分析してください。

レース：
{race_name}

出走選手・並び：
{riders}

追加情報：
{extra_info}

点数条件：
{point_instruction}

重要：

可能な限りWeb検索を利用して、
選手の過去成績、直近成績、走り方、
脚質、決まり手を調査してください。

スクショが添付されている場合は、
画像から出走表、並び、AI印、
過去成績などを読み取ってください。

内部では以下の順番で考えてください。

1. 全選手評価
2. 過去成績
3. 直近の調子
4. 脚質と決まり手
5. ライン分析
6. 複数の展開予想
7. 1着・2着・3着の個別評価
8. 三連単候補比較
9. 指定点数への調整
10. 最終点数を再確認

説明よりも、
最終フォーメーションの精度を
最優先してください。
"""

    content = [
        {
            "type": "input_text",
            "text": user_text,
        }
    ]

    if uploaded_images:
        for image in uploaded_images:
            content.append(
                make_image_content(image)
            )

    with st.spinner(
        "過去成績・近況・走り・"
        "ライン・展開をAIが分析中..."
    ):

        try:

            response = client.responses.create(
                model="gpt-5.6",
                instructions=SYSTEM_PROMPT,
                tools=[
                    {
                        "type": "web_search",
                    }
                ],
                input=[
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
            )

            answer = response.output_text

            st.divider()
            st.subheader("🤖 AI ガチ分析結果")
            st.markdown(answer)

        except Exception as e:

            st.error(
                "AI分析中にエラーが発生しました。"
            )

            # 原因を完全表示
            st.code(
                repr(e),
                language="text",
            )

            error_text = repr(e)

            if "ascii" in error_text.lower():
                st.warning(
                    "APIキーまたはSecrets設定に"
                    "日本語・全角文字・不要な文字が"
                    "混ざっている可能性があります。"
                )

# ==========================================
# 注意
# ==========================================

st.divider()

st.caption(
    "※AI予想は参考情報です。"
    "過去データや展開を分析しますが、"
    "的中を保証するものではありません。"
)
