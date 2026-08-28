import itertools
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

st.set_page_config(page_title="競輪AI v1", layout="wide")
REQ=["race_id","rider","score","S","H","B","style","line","recent_win_rate"]
FEAT=["score","S","H","B","recent_win_rate","score_gap","score_rank","line_size","line_score","style_num"]

def prep(df):
    df=df.copy()
    for c in ["score","S","H","B","recent_win_rate"]:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    for c in ["race_id","rider","style","line"]:
        df[c]=df[c].astype(str)
    return df

def features(df):
    x=prep(df)
    g=x.groupby("race_id")
    x["score_gap"]=x["score"]-g["score"].transform("mean")
    x["score_rank"]=g["score"].rank(ascending=False)
    x["line_size"]=x.groupby(["race_id","line"])["rider"].transform("count")
    x["line_score"]=x.groupby(["race_id","line"])["score"].transform("sum")
    x["style_num"]=x["style"].map({"逃":3,"先":3,"両":2,"捲":2,"追":1}).fillna(2)
    return x

def train(hist):
    x=features(hist)
    X=x[FEAT].replace([np.inf,-np.inf],0).fillna(0)
    y=pd.to_numeric(x["finish"],errors="coerce").eq(1).astype(int)
    m=make_pipeline(StandardScaler(),HistGradientBoostingClassifier(
        max_iter=250,learning_rate=.05,max_leaf_nodes=15,l2_regularization=1,random_state=42))
    m.fit(X,y)
    return m

def predict(race,model=None):
    x=features(race)
    X=x[FEAT].replace([np.inf,-np.inf],0).fillna(0)
    if model:
        p=model.predict_proba(X)[:,1]
    else:
        z=.075*(x.score-x.score.mean())+1.8*(x.recent_win_rate-x.recent_win_rate.mean())+.12*x.S+.025*x.H+.02*x.B+.06*(x.line_score-x.line_score.mean())
        z-=z.max(); p=np.exp(z)
    p=np.maximum(p,1e-12); p/=p.sum()
    x["p1"]=p
    return x.sort_values("p1",ascending=False).reset_index(drop=True)

def triples(x):
    ids=list(x.rider); p=dict(zip(ids,x.p1)); out=[]
    for a,b,c in itertools.permutations(ids,3):
        den2=1-p[a]; den3=1-p[a]-p[b]
        pr=p[a]*(p[b]/den2 if den2>0 else 0)*(p[c]/den3 if den3>0 else 0)
        out.append((a,b,c,pr))
    t=pd.DataFrame(out,columns=["1着","2着","3着","prob"])
    t.prob/=t.prob.sum()
    return t.sort_values("prob",ascending=False).reset_index(drop=True)

def choose(t,n=12):
    score=t.prob*100
    if t.odds.notna().any():
        ev=t.prob*t.odds
        score=ev.fillna(score)
    chosen=[]; c2={}; c1={}
    for i in score.sort_values(ascending=False).index:
        r=t.loc[i]
        if c2.get(r["2着"],0)>=4: continue
        val=score.loc[i]/(1+.18*c2.get(r["2着"],0)+.06*c1.get(r["1着"],0))
        chosen.append((val,i))
    chosen=sorted(chosen,reverse=True)
    ans=[]
    for _,i in chosen:
        ans.append(i); r=t.loc[i]
        c2[r["2着"]]=c2.get(r["2着"],0)+1; c1[r["1着"]]=c1.get(r["1着"],0)+1
        if len(ans)==n: break
    return t.loc[ans]

st.title("競輪AI v1")
st.caption("過去データ → 特徴量 → 1着確率 → 三連単210通り → オッズ/期待値 → 12点")

race_file=st.sidebar.file_uploader("予想レースCSV",type="csv")
hist_file=st.sidebar.file_uploader("過去データCSV（任意）",type="csv")
st.sidebar.write("予想CSV必須:",", ".join(REQ))
st.sidebar.write("過去CSVは上記＋finish(1〜7)")

if race_file is None:
    st.info("sample_race.csv をアップロードして試してください。")
    st.stop()

race=prep(pd.read_csv(race_file))
miss=[c for c in REQ if c not in race.columns]
if miss:
    st.error("不足列: "+", ".join(miss)); st.stop()

model=None
if hist_file is not None:
    hist=prep(pd.read_csv(hist_file))
    if "finish" not in hist.columns:
        st.error("過去データにはfinish列が必要です。"); st.stop()
    model=train(hist)
    st.success(f"過去データ {len(hist):,}行で学習しました。")
else:
    st.warning("過去データなし：コールドスタート評価です。")

rid=st.selectbox("レース",race.race_id.unique())
x=predict(race[race.race_id==rid],model)
view=x[["rider","score","S","H","B","style","line","recent_win_rate","p1"]].copy()
view["p1"]=view.p1.map(lambda v:f"{v*100:.1f}%")
st.subheader("1着確率")
st.dataframe(view,use_container_width=True,hide_index=True)

st.subheader("オッズ（任意・最後に入力）")
txt=st.text_area("例：1-4-5 8.4",height=100)
t=triples(x); odds={}
for line in txt.splitlines():
    z=line.replace(","," ").split()
    if len(z)>=2:
        try: odds[tuple(z[0].replace("-"," ").split())]=float(z[1])
        except: pass
t["odds"]=[odds.get((a,b,c),np.nan) for a,b,c in zip(t["1着"],t["2着"],t["3着"])]
t["ev"]=t.prob*t.odds
sel=choose(t)
st.subheader("最終12点")
st.dataframe(sel[["1着","2着","3着","prob","odds","ev"]].rename(columns={"prob":"確率","odds":"オッズ","ev":"期待値"}),use_container_width=True,hide_index=True)
st.code("\n".join(f"{r['1着']}-{r['2着']}-{r['3着']}" for _,r in sel.iterrows()))

st.subheader("三連単210通り")
allv=t.copy(); allv["確率"]=allv.prob.map(lambda v:f"{v*100:.3f}%")
st.dataframe(allv.head(30)[["1着","2着","3着","確率","odds","ev"]],use_container_width=True,hide_index=True)
