import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# ======================
# 🔐 PASSWORD PROTECTION
# ======================
def check_password():
    def password_entered():
        if st.session_state["password"] == "nm123":  # <-- CHANGE THIS
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔐 Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔐 Enter Password", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect Password")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ======================
# STYLE
# ======================
st.markdown("""
<style>
.stApp { background-color: #F5F7FB; }
.block-container { padding-top: 0.8rem; padding-bottom: 0.8rem; }
h1 { font-size: 22px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 TikTok Retention KOL Dashboard")

# ======================
# FORMATTER
# ======================
def short(x):
    try:
        x = float(x)
    except:
        return "0"

    if x >= 1_000_000_000:
        return f"{x/1_000_000_000:.1f}B"
    elif x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    elif x >= 1_000:
        return f"{x/1_000:.1f}K"
    else:
        return str(int(x))

# ======================
# LOAD DATA
# ======================
@st.cache_data
def load_data():
    df = pd.read_csv(
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZlYIU2Otc6P4CUI-1kQZXDKavGHWXCAU-y6rPzUeAdDV0buknnwxAHBe4ceTcKAFygKM_r-bZ5Ppw/pub?gid=320877529&single=true&output=csv"
    )

    df['week_start'] = pd.to_datetime(df['week_start'], errors='coerce')
    df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')

    for col in ['product','affiliate_handle','kol_bd','video_status','tier']:
        df[col] = df[col].fillna("Unknown").astype(str)

    df['gmv'] = df['gmv'].astype(str).str.replace(",", "")
    df['gmv'] = pd.to_numeric(df['gmv'], errors='coerce').fillna(0)

    return df

df = load_data()

# ======================
# FILTERS
# ======================
col1, col2, col3, col4, col5 = st.columns(5)

handles_sel = col1.multiselect("Affiliate", sorted(df['affiliate_handle'].unique()))
products_sel = col2.multiselect("Product", sorted(df['product'].unique()))
bds_sel = col3.multiselect("KOL BD", sorted(df['kol_bd'].unique()))
tiers_sel = col4.multiselect("Tier", sorted(df['tier'].unique()))

weeks = (
    df[['week','week_start']]
    .drop_duplicates()
    .sort_values('week_start')['week']
    .tolist()
)

weeks_sel = col5.multiselect("Week (Scorecard Only)", weeks)

# ======================
# FILTER LOGIC
# ======================
mask = pd.Series(True, index=df.index)

if handles_sel:
    mask &= df['affiliate_handle'].isin(handles_sel)
if products_sel:
    mask &= df['product'].isin(products_sel)
if bds_sel:
    mask &= df['kol_bd'].isin(bds_sel)
if tiers_sel:
    mask &= df['tier'].isin(tiers_sel)

df_chart = df[mask]

mask_score = mask.copy()
if weeks_sel:
    mask_score &= df['week'].isin(weeks_sel)

df_score = df[mask_score]

# ======================
# SCORECARD (FIXED UNIQUE)
# ======================
def agg(d):
    if d.empty:
        return 0, 0, 0, 0, 0

    total_gmv = d['gmv'].sum()

    # ✅ UNIQUE COUNT ONLY
    total_video = d['video_id'].nunique()
    total_kol = d['affiliate_handle'].nunique()

    video_gmv = d.loc[d['gmv'] > 0, 'video_id'].nunique()
    kol_gmv = d.loc[d['gmv'] > 0, 'affiliate_handle'].nunique()

    return total_gmv, total_video, total_kol, video_gmv, kol_gmv

gmv_now, vid_now, kol_now, vid_gmv_now, kol_gmv_now = agg(df_score)

def delta(curr, prev):
    if prev == 0:
        return f"+100% (+{short(curr)})" if curr else "0% (0)"
    change = curr - prev
    pct = change / prev * 100
    sign_pct = "+" if pct >= 0 else ""
    sign_val = "+" if change >= 0 else ""
    return f"{sign_pct}{pct:.1f}% ({sign_val}{short(abs(change))})"

colA, colB, colC, colD, colE = st.columns(5)

if len(weeks_sel) == 1:
    week_selected = weeks_sel[0]

    week_map = df[['week','week_start']].drop_duplicates().sort_values('week_start')
    current_ws = week_map[week_map['week'] == week_selected]['week_start'].values[0]

    prev_row = week_map[week_map['week_start'] < current_ws]

    if not prev_row.empty:
        prev_ws = prev_row.iloc[-1]['week_start']

        df_prev = df[
            (df['week_start'] == prev_ws) &
            mask
        ]
    else:
        df_prev = pd.DataFrame()

    gmv_prev, vid_prev, kol_prev, vid_gmv_prev, kol_gmv_prev = agg(df_prev)

    colA.metric("GMV", short(gmv_now), delta(gmv_now, gmv_prev))
    colB.metric("Total Video", vid_now, delta(vid_now, vid_prev))
    colC.metric("Total KOL", kol_now, delta(kol_now, kol_prev))
    colD.metric("Video With GMV", vid_gmv_now, delta(vid_gmv_now, vid_gmv_prev))
    colE.metric("KOL With GMV", kol_gmv_now, delta(kol_gmv_now, kol_gmv_prev))

else:
    colA.metric("GMV", short(gmv_now))
    colB.metric("Total Video", vid_now)
    colC.metric("Total KOL", kol_now)
    colD.metric("Video With GMV", vid_gmv_now)
    colE.metric("KOL With GMV", kol_gmv_now)

# ======================
# WEEKLY AGG
# ======================
weekly = df_chart.groupby('week_start').agg({
    'gmv':'sum',
    'post_count':'sum',
    'video_id':'nunique'
}).reset_index().sort_values('week_start')

# ======================
# LINE 1
# ======================
colD, colE = st.columns(2)

gmv_tier = df_chart.groupby(['week_start','tier'])['gmv'].sum().reset_index()
gmv_all = df_chart.groupby('week_start')['gmv'].sum().reset_index()
gmv_all['tier'] = 'All'

gmv_combined = pd.concat([gmv_tier, gmv_all])

fig = px.line(gmv_combined, x='week_start', y='gmv', color='tier', title="Weekly GMV")
for t in fig.data:
    t.update(mode='lines+markers+text',
             text=[short(v) for v in t.y],
             textposition='top center')
colD.plotly_chart(fig, use_container_width=True)

post_tier = df_chart.groupby(['week_start','tier'])['post_count'].sum().reset_index()
post_all = df_chart.groupby('week_start')['post_count'].sum().reset_index()
post_all['tier'] = 'All'

post_combined = pd.concat([post_tier, post_all])

fig = px.line(post_combined, x='week_start', y='post_count',
              color='tier', title="Weekly New Video Post")
for t in fig.data:
    t.update(mode='lines+markers+text',
             text=[short(v) for v in t.y],
             textposition='top center')
colE.plotly_chart(fig, use_container_width=True)

# ======================
# LINE 2
# ======================
colF, colG = st.columns(2)

video_status = df_chart.groupby(['week_start','video_status'])['video_id'].nunique().reset_index()
video_all = df_chart.groupby('week_start')['video_id'].nunique().reset_index()
video_all['video_status'] = 'All'

video_combined = pd.concat([video_status, video_all])

fig = px.line(video_combined, x='week_start', y='video_id',
              color='video_status',
              title="Weekly Total Video Based on Status")

for t in fig.data:
    t.update(mode='lines+markers+text',
             text=[short(v) for v in t.y],
             textposition='top center')

colF.plotly_chart(fig, use_container_width=True)

# ======================
# WEEKLY KOL POST VIDEO
# ======================
kol_post = df_chart[df_chart['post_count'] > 0]

kol_tier = kol_post.groupby(['week_start','tier'])['affiliate_handle'].nunique().reset_index()
kol_all = kol_post.groupby('week_start')['affiliate_handle'].nunique().reset_index()
kol_all['tier'] = 'All'

kol_combined = pd.concat([kol_tier, kol_all])

fig = px.line(kol_combined, x='week_start', y='affiliate_handle',
              color='tier',
              title="Weekly KOL Post Video")

for t in fig.data:
    t.update(mode='lines+markers+text',
             text=[short(v) for v in t.y],
             textposition='top center')

colG.plotly_chart(fig, use_container_width=True)

# ======================
# LINE 3
# ======================
colH, colI = st.columns(2)

gmv_status = df_chart.groupby(['week_start','video_status'])['gmv'].sum().reset_index()
gmv_all = df_chart.groupby('week_start')['gmv'].sum().reset_index()
gmv_all['video_status'] = 'All'

gmv_combined = pd.concat([gmv_status, gmv_all])

fig = px.line(gmv_combined, x='week_start', y='gmv',
              color='video_status',
              title="Weekly GMV by Video Status")

for t in fig.data:
    t.update(mode='lines+markers+text',
             text=[short(v) for v in t.y],
             textposition='top center')

colH.plotly_chart(fig, use_container_width=True)

pie = df_chart[df_chart['gmv'] > 0].groupby('video_status')['gmv'].sum().reset_index()

fig = px.pie(pie, names='video_status', values='gmv',
             title="Percentage GMV Based On Video Status")

fig.update_traces(
    text=[f"{l}<br>({short(v)})" for l,v in zip(pie['video_status'], pie['gmv'])],
    textinfo='percent+text'
)

colI.plotly_chart(fig, use_container_width=True)

# ======================
# TOP 5
# ======================
colJ, colK = st.columns(2)

top_kol = df_chart.groupby('affiliate_handle')['gmv'].sum().nlargest(5).reset_index()
fig = px.bar(top_kol, x='gmv', y='affiliate_handle',
             orientation='h',
             text=top_kol['gmv'].apply(short),
             title="Top 5 KOL")
fig.update_layout(yaxis=dict(autorange="reversed"))
colJ.plotly_chart(fig, use_container_width=True)

top_bd = df_chart.groupby('kol_bd')['gmv'].sum().nlargest(5).reset_index()
fig = px.bar(top_bd, x='gmv', y='kol_bd',
             orientation='h',
             text=top_bd['gmv'].apply(short),
             title="Top 5 BD")
fig.update_layout(yaxis=dict(autorange="reversed"))
colK.plotly_chart(fig, use_container_width=True)

# ======================
# RAW DATA
# ======================
st.subheader("📋 Raw Data")
st.dataframe(df_chart, height=200)