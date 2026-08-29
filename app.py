# -*- coding: utf-8 -*-

import os
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
    "スクショや出走表を入力すると、AIが過去成績・近況・脚質・ライン・展開を調査して三連単フォーメーションを作成します。"
)

# ==========================================
# APIキー取得
# ==========================================

api_key = ""

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY", "")

if not api_key:
    st.error("OPENAI_API_KEY が設定されていません。")
    st.stop()

# 明示的にUTF-8文字列へ変換
api_key = str(api_key).strip()

client = OpenAI(
    api_key=api_key,
    timeout=120.0,
    max_retries=2,
)

# ==========================================
# AIへの指示
# ==========================================

SYSTEM_PROMPT = """
あなたは競輪の三連単予想を専門にする高度な競輪データ分析AIです。

目的は、単純な競走得点順・人気順・AI印のコピーではありません。
可能な限りWeb検索を使い、実際の選手データとレース展開を分析して、
最も実戦的な三連単フォーメーションを作成してください。

【必ず調べること】

可能な限り以下を確認してください。

・選手の過去成績
・直近成績
・直近の着順だけでなくレース内容
・競走得点
・勝率、連対率、3連対率
・決まり手
・S、H、B
・脚質
・先行力
・捲り力
・追込み能力
・番手戦の強さ
・直近の調子の上昇下降
・ライン構成
・各ラインの長さ
・並び
・主導権争い
・過去対戦
・バンク特性

【最重要ルール】

1. 最初にオッズで予想を決めない。
2. まずデータと展開で評価を作る。
3. オッズは最後に期待値確認として見るだけ。
4. 存在しないデータを作らない。
5. 分からない情報を推測で事実のように書かない。
6. AI印や既存予想をそのままコピーしない。
7. 既存予想と違う結論になっても問題ない。

【分析手順】

STEP 1
全選手の能力と近況を評価する。

STEP 2
ライン構成を分析する。

誰が先頭で、誰が番手で、誰が3番手か。
各ラインの強さだけでなく、レース中に崩れる可能性も考える。

STEP 3
最低3パターンの展開を考える。

A：本命ラインが主導権を取る
B：別線が捲る
C：先行争いから番手や追込みが浮上する

必要ならさらに展開を追加する。

STEP 4
1着・2着・3着を別々に評価する。

単純な能力順位を
1着・2着・3着に並べるだけではダメ。

それぞれについて、

・1着になる可能性
・2着になる可能性
・3着になる可能性
・展開がハマった場合の浮上可能性

を別々に考える。

【フォーメーション作成ルール】

明確な1強でない限り、
1着候補は原則2人程度にする。

1着と2着を固定した買い方を何度も繰り返さない。

悪い例：

1-2-345
1-2-367

このような1-2固定を繰り返す買い方は禁止。

展開に応じて、

1が1着で2が2着
2が1着で1が2着
別の選手が2着に浮上

などを自然に考慮する。

変則的すぎるフォーメーションは避け、
普通で見やすい実戦的なフォーメーションにする。

【点数】

ユーザーが指定した最大点数を絶対に超えない。

ユーザーが12点なら最大12点。
20点なら最大20点。

できるだけ指定された点数に近づける。

必ず実際に三連単を展開し、
重複を除いた最終点数を確認する。

【出力形式】

回答は長すぎないようにする。

最初に、

【AI結論】
◎ 本命
○ 対抗
▲ 単穴
☆ 穴

次に、

【想定展開】

を短く書く。

最後に必ず、

【最終フォーメーション】

を出す。

例：

7-13-12356
1-7-12356

合計：10点

最後のフォーメーションは、
実際の展開に基づいた自然な形にすること。

最重要なのは説明の長さではなく、
買い目の精度である。
"""

# ==========================================
# 入力エリア
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
# スクショアップロード
# ==========================================

st.subheader("📸 出走表スクショ（任意）")

uploaded_images = st.file_uploader(
    "出走表・予想・直近成績などのスクショをアップロード",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)

if uploaded_images:
    st.success(f"{len(uploaded_images)}枚の画像を読み込みました。")

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
    "スクショだけでも分析可能です。選手名や並びをテキストでも入力すると精度が上がります。"
)

# ==========================================
# 画像をOpenAI形式へ変換
# ==========================================

def make_image_content(uploaded_file):
    image_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type

    if not mime_type:
        mime_type = "image/jpeg"

    return {
        "type": "input_image",
        "image_url": (
            f"data:{mime_type};base64,"
            + __import__("base64").b64encode(image_bytes).decode("ascii")
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
        st.error("出走選手情報を入力するか、スクショをアップロードしてください。")
        st.stop()

    point_instruction = (
        f"最終買い目は最大{target_points}点まで。"
        f"絶対に{target_points}点を超えない。"
        f"できるだけ{target_points}点に近づける。"
    )

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
まず可能な限りWeb検索を利用して、
選手の過去成績・近況・走り方を調査してください。

スクショが添付されている場合は、
画像から出走表、並び、AI印、成績なども読み取ってください。

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

説明よりも最終フォーメーションの精度を最優先してください。
"""

    content = [
        {
            "type": "input_text",
            "text": user_text,
        }
    ]

    if uploaded_images:
        for image in uploaded_images:
            content.append(make_image_content(image))

    with st.spinner(
        "過去成績・近況・走り・ライン・展開をAIがガチ分析中..."
    ):

        try:
            response = client.responses.create(
                model="gpt-5.6",
                instructions=SYSTEM_PROMPT,
                tools=[
                    {
                        "type": "web_search",
                        "search_context_size": "high",
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
            st.error("AI分析中にエラーが発生しました。")
            st.code(str(e))

            st.info(
                "まず requirements.txt の openai を最新版にしてください。"
            )

# ==========================================
# 注意
# ==========================================

st.divider()

st.caption(
    "※AI予想は参考情報です。過去データや展開を分析しますが、的中を保証するものではありません。"
)
