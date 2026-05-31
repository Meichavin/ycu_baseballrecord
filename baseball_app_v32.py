# baseball_app_v32.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- 【修正】フォントの直接読み込み設定 ---
FONT_PATH = "NotoSansJP-Regular.ttf"

if os.path.exists(FONT_PATH):
    # フォントファイルをmatplotlibに登録
    fm.fontManager.addfont(FONT_PATH)
    prop = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = prop.get_name()
else:
    # 万が一ファイルがない場合のバックアップ
    plt.rcParams['font.family'] = 'sans-serif'
# -----------------------------------------

# ---------------------------------------------------------
# 【重要】セキュリティ設定（任意のパスワードを設定してください）
# ---------------------------------------------------------
ADMIN_PASSWORD = "めいちゃびん" 

DATA_FILE = "pitch_data.csv"
PITCHER_FILE = "pitchers.csv" # 投手一覧を保存するファイル

st.set_page_config(page_title="ycu野球投球分析 Ver3.2", layout="wide")

# パスワード認証用のセッション状態初期化
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- パスワードログイン画面 ---
if not st.session_state.authenticated:
    st.title("🔒 ログイン管理画面")
    pwd_input = st.text_input("認証パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pwd_input == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.success("認証に成功しました！")
            st.rerun()
        else:
            st.error("パスワードが正しくありません。")
    st.stop() # 認証されるまでこれ以降のコードを実行しない

# --- 認証後のメインアプリ処理 ---
cols = ["日時", "投手名", "モード", "打者左右", "球種", "イベント", "ボール", "ストライク",
        "カウント", "打席結果", "決め球", "最終カウント", "初球"]

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
else:
    df = pd.DataFrame(columns=cols)

# 投手リストの読み込み
if os.path.exists(PITCHER_FILE):
    pitcher_df = pd.read_csv(PITCHER_FILE)
    pitcher_list = pitcher_df["投手名"].tolist()
else:
    pitcher_list = ["未登録"]

for k, v in {"balls": 0, "strikes": 0, "last_pitch": ""}.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.title("ycu野球投球分析 Ver3.2")

tab_in, tab_s, tab_h, tab_m, tab_set = st.tabs(
    ["入力", "ストライク率", "被打率", "投手指標", "設定"]
)

with tab_in:
    if pitcher_list == ["未登録"]:
        st.warning("⚠️ 投手が登録されていません。「設定」タブから投手を登録してください。")
    
    # 基本設定エリア（コンパクトに横並び）
    c_mode1, c_mode2, c_mode3 = st.columns(3)
    with c_mode1:
        current_pitcher = st.selectbox("投球中の投手", pitcher_list)
    with c_mode2:
        mode = st.radio("モード", ["ブルペン", "試合"], horizontal=True)
    with c_mode3:
        batter = st.radio("打者", ["右", "左"], horizontal=True) if mode == "試合" else "不明"

    # 現在のカウント表示
    st.markdown(f"###　現在のカウント: B**{st.session_state.balls}** -S **{st.session_state.strikes}**")

    # 初球フラグの事前判定
    is_first_pitch = (st.session_state.balls == 0 and st.session_state.strikes == 0)

    # ---------------------------------------------------------
    # 【メイン】投球記録の1タップマトリックスUI
    # ---------------------------------------------------------
    st.markdown("###　1タップ投球記録")
    st.caption("球種と結果が交わるボタンをタップすると、その場で即時記録されます。")

    pitch_choices = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カット"]
    event_list = ["ストライク", "ボール", "ファウル", "空振り"]

    # グリッドのヘッダーを作成
    cols_grid = st.columns([1.5, 2, 2, 2, 2])
    with cols_grid[0]:
        st.write("**球種**")
    for i, ev in enumerate(event_list):
        with cols_grid[i+1]:
            st.markdown(f"**{ev}**")

    # 各球種ごとの行を生成
    for p in pitch_choices:
        cols_grid = st.columns([1.5, 2, 2, 2, 2])
        with cols_grid[0]:
            st.markdown(f"**{p}**")
        
        for i, ev in enumerate(event_list):
            with cols_grid[i+1]:
                if st.button(f"{ev}", key=f"btn_{p}_{ev}", use_container_width=True, disabled=(pitcher_list == ["未登録"])):
                    b, s = st.session_state.balls, st.session_state.strikes
                    st.session_state.last_pitch = p

                    # カウント処理
                    if ev == "ボール":
                        b += 1
                    elif ev == "ファウル":
                        if s < 2: s += 1
                    else:  # ストライク、空振り
                        if s < 2: s += 1

                    row = {
                        "日時": datetime.now(), "投手名": current_pitcher, "モード": mode, "打者左右": batter,
                        "球種": p, "イベント": ev, "ボール": b, "ストライク": s,
                        "カウント": f"{b}-{s}", "打席結果": "", "決め球": "", "最終カウント": "",
                        "初球": is_first_pitch
                    }

                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

                    if b >= 4:
                        st.warning("四球でカウントリセット")
                        b, s = 0, 0

                    st.session_state.balls = b
                    st.session_state.strikes = s
                    df.to_csv(DATA_FILE, index=False)
                    st.rerun()

    # ---------------------------------------------------------
    # 【試合モード限定】打席結果の1タップUI
    # ---------------------------------------------------------
    if mode == "試合":
        st.write("---")
        st.markdown("### 打席結果保存")
        
        pa_list = ["アウト", "三振", "四球", "死球", "単打", "二塁打", "三塁打", "本塁打", "失策"]
        
        pa_cols = st.columns(3)
        for idx, pa in enumerate(pa_list):
            with pa_cols[idx % 3]:
                if st.button(f"💥 {pa}", key=f"pa_{pa}", use_container_width=True, disabled=(pitcher_list == ["未登録"])):
                    row = {
                        "日時": datetime.now(), "投手名": current_pitcher, "モード": "試合", "打者左右": batter,
                        "球種": "", "イベント": "打席終了",
                        "ボール": st.session_state.balls,
                        "ストライク": st.session_state.strikes,
                        "カウント": "",
                        "打席結果": pa,
                        "決め球": st.session_state.last_pitch,
                        "最終カウント": f"{st.session_state.balls}-{st.session_state.strikes}",
                        "初球": is_first_pitch
                    }
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                    st.session_state.balls = 0
                    st.session_state.strikes = 0
                    df.to_csv(DATA_FILE, index=False)
                    st.success(f"{pa} を記録しました。カウントをリセットします。")
                    st.rerun()

with tab_s:
    st.subheader("投手別ストライク率分析")
    filter_pitcher = st.selectbox("分析対象の投手を選択", ["全員"] + pitcher_list, key="sb_s")
    
    # 投手フィルターの適用
    active_df = df if filter_pitcher == "全員" else df[df["投手名"] == filter_pitcher]
    pitch_df = active_df[active_df["イベント"].isin(["ストライク", "ボール", "ファウル", "空振り"])].copy()

    if len(pitch_df):
        pitch_df["StrikeFlag"] = pitch_df["イベント"].isin(["ストライク", "ファウル", "空振り"]).astype(int)

        strike = pitch_df.groupby("球種").agg(投球数=("StrikeFlag", "count"), ストライク率=("StrikeFlag", "mean"))
        strike["ストライク率"] *= 100

        with st.expander("球種別ストライク率"):
            st.dataframe(strike.round(1))

        with st.expander("右左別ストライク率"):
            side = pitch_df.groupby("打者左右").agg(投球数=("StrikeFlag", "count"), ストライク率=("StrikeFlag", "mean"))
            side["ストライク率"] *= 100
            st.dataframe(side.round(1))

        with st.expander("カウント別ストライク率"):
            cnt = pitch_df.groupby("カウント").agg(投球数=("StrikeFlag", "count"), ストライク率=("StrikeFlag", "mean"))
            cnt["ストライク率"] *= 100
            st.dataframe(cnt.round(1))

        st.subheader("球種別ストライク率グラフ")
        fig, ax = plt.subplots()
        strike["ストライク率"].plot(kind="bar", ax=ax)
        st.pyplot(fig)
    else:
        st.info("データがありません。")

with tab_h:
    st.subheader("投手別被打率分析")
    filter_pitcher_h = st.selectbox("分析対象の投手を選択", ["全員"] + pitcher_list, key="sb_h")
    
    active_df = df if filter_pitcher_h == "全員" else df[df["投手名"] == filter_pitcher_h]
    result_df = active_df[active_df["打席結果"].isin(["アウト", "単打", "二塁打", "三塁打", "本塁打"])].copy()

    if len(result_df):
        result_df["Hit"] = result_df["打席結果"].isin(["単打", "二塁打", "三塁打", "本塁打"]).astype(int)
        result_df["AB"] = 1

        with st.expander("球種別被打率"):
            batting = result_df.groupby("決め球").agg(打数=("AB", "sum"), 被安打=("Hit", "sum"))
            batting["被打率"] = batting["被安打"] / batting["打数"]
            st.dataframe(batting.round(3))

        with st.expander("右左別被打率"):
            sideb = result_df.groupby("打者左右").agg(打数=("AB", "sum"), 被安打=("Hit", "sum"))
            sideb["被打率"] = sideb["被安打"] / sideb["打数"]
            st.dataframe(sideb.round(3))

        with st.expander("カウント別被打率"):
            cb = result_df.groupby("最終カウント").agg(打数=("AB", "sum"), 被安打=("Hit", "sum"))
            cb["被打率"] = cb["被安打"] / cb["打数"]
            st.dataframe(cb.round(3))
    else:
        st.info("データがありません。")

with tab_m:
    st.subheader("投手別詳細指標")
    filter_pitcher_m = st.selectbox("分析対象の投手を選択", ["全員"] + pitcher_list, key="sb_m")
    
    active_df = df if filter_pitcher_m == "全員" else df[df["投手名"] == filter_pitcher_m]
    pa_df = active_df[active_df["打席結果"] != ""]
    
    if len(pa_df):
        pa = len(pa_df)
        k = (pa_df["打席結果"] == "三振").sum()
        bb = (pa_df["打席結果"] == "四球").sum()

        c1, c2 = st.columns(2)
        c1.metric("K%", f"{100*k/pa:.1f}%")
        c2.metric("BB%", f"{100*bb/pa:.1f}%")

    pitch_df = active_df[active_df["イベント"].isin(["ストライク", "ボール", "ファウル", "空振り"])].copy()
    
    col_m1, col_m2, col_m3 = st.columns(3)
    
    swing_events = ["空振り", "ファウル"]
    swings = pitch_df["イベント"].isin(swing_events).sum()
    whiffs = (pitch_df["イベント"] == "空振り").sum()

    with col_m1:
        st.metric("総球数", len(pitch_df))
        if swings > 0:
            whiff_rate = whiffs / swings
            st.metric("空振り率", f"{whiff_rate*100:.1f}%")
        else:
            st.metric("空振り率", "0.0%")

    first_pitch_df = pitch_df[pitch_df["初球"].astype(str).str.lower() == 'true']

    with col_m2:
        if len(first_pitch_df) > 0:
            first_strike = first_pitch_df["イベント"].isin(["ストライク", "ファウル", "空振り"]).sum()
            fps = first_strike / len(first_pitch_df)
            st.metric("初球ストライク率", f"{fps*100:.1f}%")
        else:
            st.metric("初球ストライク率", "0.0%")

    whiff_df = pitch_df.copy()
    whiff_df["Swing"] = whiff_df["イベント"].isin(["空振り", "ファウル"]).astype(int)
    whiff_df["Whiff"] = (whiff_df["イベント"] == "空振り").astype(int)

    if len(whiff_df) > 0:
        pitch_whiff = whiff_df.groupby("球種").agg(スイング数=("Swing", "sum"), 空振り数=("Whiff", "sum"))
        pitch_whiff = pitch_whiff[pitch_whiff["スイング数"] > 0]
        pitch_whiff["空振り率"] = (pitch_whiff["空振り数"] / pitch_whiff["スイング数"]) * 100

        st.write("---")
        with st.expander("球種別空振り率"):
            st.dataframe(pitch_whiff.round(1))

    if len(pitch_df):
        st.subheader("球種割合")
        counts = pitch_df["球種"].value_counts()
        fig, ax = plt.subplots()
        ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%")
        st.pyplot(fig)

with tab_set:
    st.subheader("投手登録")
    new_pitcher = st.text_input("新しい投手の名前を入力してください")
    if st.button("投手を新規登録"):
        if new_pitcher:
            # 既存のリストを更新
            if pitcher_list == ["未登録"]:
                updated_list = [new_pitcher]
            else:
                updated_list = pitcher_list + [new_pitcher]
            
            # 重複排除して保存
            updated_list = list(set(updated_list))
            pd.DataFrame({"投手名": updated_list}).to_csv(PITCHER_FILE, index=False)
            st.success(f"「{new_pitcher}」投手を登録しました！")
            st.rerun()
        else:
            st.error("名前を入力してください。")

    if st.button("投手リストをリセット"):
        if os.path.exists(PITCHER_FILE):
            os.remove(PITCHER_FILE)
        st.warning("投手を初期化しました。")
        st.rerun()

    st.write("---")
    st.subheader("データ確認")
    st.dataframe(df.tail(100))

    idx = st.number_input("削除する行番号(index)", 0, max(0, len(df)-1) if len(df) > 0 else 0, 0)

    if st.button("指定行削除") and len(df) > 0:
        df = df.drop(index=idx).reset_index(drop=True)
        df.to_csv(DATA_FILE, index=False)
        st.success("削除しました")

    if st.button("最後の1行を削除") and len(df) > 0:
        df = df.iloc[:-1]
        df.to_csv(DATA_FILE, index=False)
        st.success("最後の1行を削除しました")

    if st.button("全データ削除"):
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_FILE, index=False)
        st.warning("全削除しました")

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSVダウンロード", csv, "pitch_data.csv", "text/csv")
