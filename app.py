# =========================================================
# フォーメーション表示
# =========================================================

def nums(v):
    if isinstance(v, tuple):
        return "".join(str(x) for x in sorted(v))
    return str(v)

st.subheader(f"🧩 最終{target_n}点をフォーメーション表示")

formation_points = []

for item in formations:

    if item[0] == "single":

        x = item[1]

        bet = "-".join(map(str, x))

        formation_points.append(
            (bet, 1)
        )

    else:

        # formationsには
        # ("rect", (a, b, c, rect))
        # の形で保存されている
        best = item[1]

        a, b, c, rect = best

        bet = f"{nums(a)}-{nums(b)}-{nums(c)}"

        formation_points.append(
            (bet, len(rect))
        )

for bet, count in formation_points:

    st.write(
        f"**{bet}**　→ {count}点"
    )

formation_total = sum(
    count for _, count in formation_points
)

st.caption(
    f"フォーメーション合計："
    f"{formation_total}点"
)

if formation_total == target_n:

    st.success(
        f"予想完了！ "
        f"最終{target_n}点で一致しています。"
    )

else:

    st.warning(
        f"フォーメーション表示は"
        f"{formation_total}点です。"
        f"最終買い目は{target_n}点です。"
    )
