# baseball_app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- フォントの直接読み込み設定 ---
FONT_PATH = "NotoSansJP-Regular.ttf"

if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    prop = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = prop.get_name()
else:
    # 万が一ファイルがない場合のバックアップ
    plt.rcParams['font.family'] = 'sans-serif'
# -----------------------------------------

ADMIN_PASSWORD = "ycu2026" 

DATA_FILE = "pitch_data.csv"
PITCHER_FILE = "pitchers.csv" 

st.set_page_config(page_title="ycu野球投球分析 Ver3.4", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

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
    st.stop() 

# カラムに「試合名」を追加
cols = ["日時", "投手名", "試合名", "モード", "打者左右", "球種", "イベント", "ボール", "ストライク",
        "カウント", "打席結果", "決め球", "最終カウント", "初球"]

# 日時のパース（ISO形式からdatetime型にパース。変換できないものはNaTに）
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df["日時"] = pd.to_datetime(df["日時"], errors="coerce")
    for c in cols:
        if c not in df.columns:
            df[c] = ""
else:
    df = pd.DataFrame(columns=cols)

if os.path.exists(PITCHER_FILE):
    pitcher_df = pd.read_csv(PITCHER_FILE)
    pitcher_list = pitcher_df["投手名"].tolist()
else:
    pitcher_list = ["未登録"]

# --- セッション状態の初期化 ---
init_states = {
    "balls": 0, 
    "strikes": 0, 
    "selected_pitch": "", 
    "selected_event": "",
    "prev_mode": "ブルペン",    
    "prev_batter": "右"        
}
for k, v in init_states.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.title("ycu野球投球分析 Ver3.4")

tab_in, tab_s, tab_h, tab_m, tab_out, tab_set = st.tabs(
    ["入力", "ストライク率", "被打率", "投手指標", "データ出力・管理", "設定"]
)

# 【新規共通関数】保存時に日時を確実にISOフォーマット(文字列)に変換する関数
def save_data(target_df):
    save_df = target_df.copy()
    if "日時" in save_df.columns:
        # datetime型オブジェクトをISO形式文字列 (YYYY-MM-DDTHH:MM:SS) に一括変換
        save_df["日時"] = pd.to_datetime(save_df["日時"]).dt.strftime('%Y-%m-%dT%H:%M:%S')
    save_df.to_csv(DATA_FILE, index=False)

# ==========================================
# 【入力タブ】
# ==========================================
with tab_in:
    if pitcher_list == ["未登録"]:
        st.warning("⚠️ 投手が登録されていません。「設定」タブから投手を登録してください。")
    
    # 基本設定エリア
    c_mode1, c_mode1_5, c_mode2, c_mode3 = st.columns(4)
    with c_mode1:
        current_pitcher = st.selectbox("投球中の投手", pitcher_list)
    with c_mode1_5:
        match_name = st.text_input("試合名・メモ", "練習", help="OP戦、春季大会、ブルペン等、データに紐付ける名前")
    with c_mode2:
        mode = st.radio("モード", ["ブルペン", "試合"], horizontal=True)
    with c_mode3:
        batter = st.radio("打者", ["右", "左"], horizontal=True) if mode == "試合" else "不明"

    # モードまたは打者の変更時にカウントを自動リセット
    if st.session_state.prev_mode != mode or (mode == "試合" and st.session_state.prev_batter != batter):
        st.session_state.balls = 0
        st.session_state.strikes = 0
        st.session_state.selected_pitch = ""
        st.session_state.selected_event = ""
        st.session_state.prev_mode = mode
        st.session_state.prev_batter = batter
        st.toast("モード/打者が変更されたため、カウントを0-0にリセットしました。")
        st.rerun()

    st.markdown(f"### 現在のカウント: ボール **{st.session_state.balls}** - ストライク **{st.session_state.strikes}**")
    is_first_pitch = (st.session_state.balls == 0 and st.session_state.strikes == 0)

    st.write("---")
    
    pitch_choices = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カット", "シュート", "シンカー"]
    event_list = ["ストライク", "ボール", "ファウル", "空振り"]
    pa_list = ["アウト", "三振", "四球", "死球", "単打", "二塁打", "三塁打", "本塁打", "失策"]

    disable_buttons = (pitcher_list == ["未登録"])

    # STEP 1: 球種の選択
    st.markdown("**1. 球種を選択**")
    pitch_cols = st.columns(4)
    for idx, p in enumerate(pitch_choices):
        with pitch_cols[idx % 4]:
            is_p_sel = (st.session_state.selected_pitch == p)
            if st.button(f"{'🟢 ' if is_p_sel else ''}{p}", key=f"pitch_{p}", type="primary" if is_p_sel else "secondary", use_container_width=True, disabled=disable_buttons):
                st.session_state.selected_pitch = p
                st.rerun()

    # STEP 2: 投球結果の選択
    if st.session_state.selected_pitch:
        st.markdown(f"**2. 「{st.session_state.selected_pitch}」の投球結果を選択**")
        ev_cols = st.columns(4)
        for idx, ev in enumerate(event_list):
            with ev_cols[idx % 4]:
                is_ev_sel = (st.session_state.selected_event == ev)
                if st.button(f"{ev}", key=f"ev_{ev}", type="primary" if is_ev_sel else "secondary", use_container_width=True):
                    st.session_state.selected_event = ev
                    
                    if mode == "ブルペン":
                        b, s = st.session_state.balls, st.session_state.strikes
                        if ev == "ボール": b += 1
                        elif ev in ["ストライク", "ファウル", "空振り"]:
                            if ev != "ファウル" or s < 2: s += 1
                        
                        # 保存時は datetime.now() のオブジェクトの状態で df に追加（保存時にISO文字列化）
                        row = {
                            "日時": datetime.now(), "投手名": current_pitcher, "試合名": match_name, "モード": mode, "打者左右": batter,
                            "球種": st.session_state.selected_pitch, "イベント": ev, "ボール": b, "ストライク": s, "カウント": f"{b}-{s}",
                            "打席結果": "", "決め球": "", "最終カウント": "", "初球": is_first_pitch
                        }
                        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                        if b >= 4: b, s = 0, 0
                        st.session_state.balls, st.session_state.strikes = b, s
                        st.session_state.selected_pitch = ""
                        st.session_state.selected_event = ""
                        save_data(df)
                        st.rerun()
                    else:
                        st.rerun()

    # STEP 3: 打席結果の選択（試合モードのみ）
    if st.session_state.selected_pitch and st.session_state.selected_event:
        p = st.session_state.selected_pitch
        ev = st.session_state.selected_event
        
        b_next, s_next = st.session_state.balls, st.session_state.strikes
        if ev == "ボール": b_next += 1
        elif ev in ["ストライク", "ファウル", "空振り"]:
            if ev != "ファウル" or s_next < 2: s_next += 1

        st.markdown(f"**3. 打席の状況に応じて以下をタップ（即時保存）**")
        col_direct, col_pa = st.columns([1, 2])
        
        with col_direct:
            st.caption("【打席が継続する場合】")
            if st.button("カウントを進めて次へ", type="primary", use_container_width=True):
                row = {
                    "日時": datetime.now(), "投手名": current_pitcher, "試合名": match_name, "モード": "試合", "打者左右": batter,
                    "球種": p, "イベント": ev, "ボール": b_next, "ストライク": s_next,
                    "カウント": f"{b_next}-{s_next}", "打席結果": "", "決め球": "", "最終カウント": "",
                    "初球": is_first_pitch
                }
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                
                if b_next >= 4:
                    st.warning("自動で四球リセットされました")
                    b_next, s_next = 0, 0
                    
                st.session_state.balls, st.session_state.strikes = b_next, s_next
                st.session_state.selected_pitch = ""
                st.session_state.selected_event = ""
                save_data(df)
                st.rerun()
                
        with col_pa:
            st.caption("【この投球で打席が終了（決着）した場合】")
            pa_cols = st.columns(3)
            for idx, pa in enumerate(pa_list):
                with pa_cols[idx % 3]:
                    if st.button(f"{pa}", key=f"pa_{pa}", use_container_width=True):
                        row = {
                            "日時": datetime.now(), "投手名": current_pitcher, "試合名": match_name, "モード": "試合", "打者左右": batter,
                            "球種": p, "イベント": ev, 
                            "ボール": b_next, "ストライク": s_next,
                            "カウント": f"{b_next}-{s_next}",
                            "打席結果": pa,
                            "決め球": p, 
                            "最終カウント": f"{st.session_state.balls}-{st.session_state.strikes}",
                            "初球": is_first_pitch
                        }
                        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                        
                        st.session_state.balls = 0
                        st.session_state.strikes = 0
                        st.session_state.selected_pitch = ""
                        st.session_state.selected_event = ""
                        
                        save_data(df)
                        st.success(f"{pa} を記録しました。")
                        st.rerun()
                        
        if st.button("❌ 選択をやり直す", use_container_width=True):
            st.session_state.selected_pitch = ""
            st.session_state.selected_event = ""
            st.rerun()
    else:
        if not st.session_state.selected_pitch:
            st.info("上のボタンから球種を選択すると、次の入力に進みます。")

# ==========================================
# 【ストライク率タブ】
# ==========================================
with tab_s:
    st.subheader("投手別ストライク率分析")

    c1, c2, c3 = st.columns(3)
    with c1:
        filter_pitcher = st.selectbox("分析対象の投手を選択", ["全員"] + pitcher_list, key="sb_s")
    with c2:
        mode_filter = st.radio("データ種別", ["全て", "試合のみ", "ブルペンのみ"], index=1, horizontal=True, key="mode_s")
    with c3:
        # 部分一致検索用テキスト入力に変更
        match_filter = st.text_input("試合名（部分一致）", "", key="match_s_input")

    active_df = df if filter_pitcher == "全員" else df[df["投手名"] == filter_pitcher]

    if mode_filter == "試合のみ":
        active_df = active_df[active_df["モード"] == "試合"]
    elif mode_filter == "ブルペンのみ":
        active_df = active_df[active_df["モード"] == "ブルペン"]

    # 試合名フィルター（部分一致）
    if match_filter.strip() != "":
        active_df = active_df[active_df["試合名"].astype(str).str.contains(match_filter.strip(), case=False, na=False)]

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
        fig, ax = plt.subplots(figsize=(8, 4))
        strike["ストライク率"].plot(kind="bar", ax=ax)
        ax.set_ylabel("ストライク率(%)")
        ax.set_xlabel("球種")
        ax.set_ylim(0, 100)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.info("データがありません。")

# ==========================================
# 【被打率タブ】
# ==========================================
with tab_h:
    st.subheader("投手別被打率分析")

    c_h1, c_h2, c_h3 = st.columns(3)
    with c_h1:
        filter_pitcher_h = st.selectbox("分析対象の投手を選択", ["全員"] + pitcher_list, key="sb_h")
    with c_h2:
        # 部分一致検索用テキスト入力に変更
        match_filter_h = st.text_input("試合名（部分一致）", "", key="match_h_input")
    with c_h3:
        st.write("") 

    active_df = df if filter_pitcher_h == "全員" else df[df["投手名"] == filter_pitcher_h]

    # 試合名フィルター（部分一致）
    if match_filter_h.strip() != "":
        active_df = active_df[active_df["試合名"].astype(str).str.contains(match_filter_h.strip(), case=False, na=False)]

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

# ==========================================
# 【投手指標タブ】
# ==========================================
with tab_m:
    st.subheader("投手別詳細指標")

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        filter_pitcher_m = st.selectbox("分析対象の投手を選択", ["全員"] + pitcher_list, key="sb_m")
    with c_m2:
        mode_filter_m = st.radio("データ種別", ["全て", "試合のみ", "ブルペンのみ"], index=1, horizontal=True, key="mode_m")
    with c_m3:
        # 部分一致検索用テキスト入力に変更
        match_filter_m = st.text_input("試合名（部分一致）", "", key="match_m_input")
    with c_m4:
        st.write("") 

    active_df = df if filter_pitcher_m == "全員" else df[df["投手名"] == filter_pitcher_m]

    if mode_filter_m == "試合のみ":
        active_df = active_df[active_df["モード"] == "試合"]
    elif mode_filter_m == "ブルペンのみ":
        active_df = active_df[active_df["モード"] == "ブルペン"]

    # 試合名フィルター（部分一致）
    if match_filter_m.strip() != "":
        active_df = active_df[active_df["試合名"].astype(str).str.contains(match_filter_m.strip(), case=False, na=False)]
        
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

    if len(pitch_df) > 0:
        pitch_df["初球"] = (
            pitch_df["初球"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "t", "yes"])
        )
        first_pitch_df = pitch_df[pitch_df["初球"]]
    else:
        first_pitch_df = pitch_df

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
        display_df = pd.DataFrame({
            "投球数": counts,
            "割合(%)": (counts / counts.sum() * 100).round(1)
        })
        st.dataframe(display_df)

        fig, ax = plt.subplots(figsize=(8, 4))
        counts.plot(kind="bar", ax=ax)
        ax.set_ylabel("投球数")
        ax.set_xlabel("球種")
        ax.set_title("球種別投球数")
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ==========================================
# 【データ出力・管理タブ】
# ==========================================
with tab_out:
    st.subheader("条件指定データ出力 (CSV)")
    
    if len(df) == 0:
        st.info("データがありません。")
    else:
        c_out1, c_out2 = st.columns(2)
        
        with c_out1:
            st.markdown("**1. 期間を指定**")
            # デフォルト表示のバグを防ぐため、データ内の日付範囲を取得、無ければ今日
            valid_dates = df["日時"].dropna()
            if len(valid_dates) > 0:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
            else:
                min_date = date.today()
                max_date = date.today()
            date_range = st.date_input("抽出する期間", [min_date, max_date], help="開始日と終了日を選択してください")
            
        with c_out2:
            st.markdown("**2. 属性で絞り込み**")
            p_filter = st.selectbox("投手名で絞り込み", ["全員"] + pitcher_list, key="out_p")
            m_filter = st.text_input("試合名でキーワード検索", "", help="空欄の場合はすべての試合・メモが対象")

        # フィルタリング処理
        filtered_df = df.copy()
        
        # 1. 日付フィルター
        if isinstance(date_range, list) or isinstance(date_range, tuple):
            if len(date_range) == 2:
                start_date = pd.to_datetime(date_range[0]).date()
                end_date = pd.to_datetime(date_range[1]).date()
                filtered_df = filtered_df[
                    (filtered_df["日時"].dt.date >= start_date) & 
                    (filtered_df["日時"].dt.date <= end_date)
                ]
        
        # 2. 投手名フィルター
        if p_filter != "全員":
            filtered_df = filtered_df[filtered_df["投手名"] == p_filter]
            
        # 3. 試合名フィルター（部分一致検索）
        if m_filter:
            filtered_df = filtered_df[filtered_df["試合名"].astype(str).str.contains(m_filter.strip(), case=False, na=False)]

        st.write("---")
        st.markdown(f"抽出結果: {len(filtered_df)} 件のデータが見つかりました")
        
        # 画面表示用データ（ISO 形式の文字列に変換して見やすく表示）
        display_df = filtered_df.copy()
        if len(display_df) > 0:
            display_df["日時"] = display_df["日時"].dt.strftime('%Y-%m-%dT%H:%M:%S')
        st.dataframe(display_df.tail(100))
        
        # ダウンロードボタン
        if len(filtered_df) > 0:
            csv_export_df = filtered_df.copy()
            csv_export_df["日時"] = csv_export_df["日時"].dt.strftime('%Y-%m-%dT%H:%M:%S')
            csv_data = csv_export_df.to_csv(index=False).encode("utf-8-sig")
            
            filename_suffix = f"{date_range[0].strftime('%Y%m%d')}_to_{date_range[1].strftime('%Y%m%d')}" if len(date_range)==2 else "filtered"
            
            st.download_button(
                label="選択した条件でCSVを出力する",
                data=csv_data,
                file_name=f"pitch_data_{filename_suffix}.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.warning("該当するデータがないため、出力ボタンを表示できません。条件を緩めてください。")

        # データの個別・一括管理機能
        st.write("---")
        st.subheader("データの削除")
        idx = st.number_input("削除する行番号(index)", 0, max(0, len(df)-1) if len(df) > 0 else 0, 0, key="del_idx")

        c_del1, c_del2, c_del3 = st.columns(3)
        with c_del1:
            if st.button("指定行削除", use_container_width=True) and len(df) > 0:
                df = df.drop(index=idx).reset_index(drop=True)
                save_data(df) # ISO一括変換保存
                st.success(f"インデックス {idx} を削除しました")
                st.rerun()
        with c_del2:
            if st.button("最後の1行を削除", use_container_width=True) and len(df) > 0:
                df = df.iloc[:-1].reset_index(drop=True)
                save_data(df) # ISO一括変換保存
                st.success("最後の1行を削除しました")
                st.rerun()
        with c_del3:
            confirm_delete = st.checkbox("本当に全データを削除する", key="confirm_delete_all")
            if confirm_delete:
                if st.button("全データ削除", type="secondary", use_container_width=True):
                    df = pd.DataFrame(columns=cols)
                    save_data(df) # 空の状態でISO整合性を保ち保存
                    st.warning("全データを完全削除しました")
                    st.rerun()

# ==========================================
# 【設定タブ】
# ==========================================
with tab_set:
    st.subheader("投手登録")
    new_pitcher = st.text_input("新しい投手の名前を入力してください")
    if st.button("投手を新規登録"):
        if new_pitcher:
            if pitcher_list == ["未登録"]:
                updated_list = [new_pitcher]
            else:
                updated_list = pitcher_list + [new_pitcher]
            
            updated_list = list(set(updated_list))
            pd.DataFrame({"投手名": updated_list}).to_csv(PITCHER_FILE, index=False)
            st.success(f"「{new_pitcher}」投手を登録しました！")
            st.rerun()
        else:
            st.error("名前を入力してください。")

    if st.button("投手リストをリセット"):
        if os.path.exists(PITCHER_FILE):
            os.remove(PITCHER_FILE)
        st.warning("投手リストを初期化しました。")
        st.rerun()
