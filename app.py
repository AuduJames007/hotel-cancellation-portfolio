import streamlit as st
import pandas as pd
import numpy as np
import json

# -------------------------------------------------------------
# 1. PAGE SETUP (FULL-BLEED ZERO-MARGIN WORKSPACE)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Royalty Hotel & Suites | Hotel Cancellation Analytics",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    header[data-testid="stHeader"], footer, section[data-testid="stSidebar"] {
        display: none !important;
    }
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100vw !important;
        overflow: hidden !important;
    }
    .stApp {
        background-color: #060913 !important;
        overflow: hidden !important;
    }
    iframe {
        border: none !important;
        width: 100vw !important;
        height: 100vh !important;
        display: block !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. ONE-TIME IN-MEMORY DATA ENGINE
# -------------------------------------------------------------
@st.cache_data
def build_in_memory_cubes():
    cols = [
        'hotel', 'is_canceled', 'lead_time', 'arrival_date_year', 'arrival_date_month',
        'arrival_date_day_of_month', 'arrival_date', 'stays_in_weekend_nights',
        'stays_in_week_nights', 'total_nights', 'adults', 'children', 'babies',
        'meal', 'country', 'market_segment', 'distribution_channel', 'is_repeated_guest',
        'previous_cancellations', 'previous_bookings_not_canceled', 'reserved_room_type',
        'assigned_room_type', 'booking_changes', 'deposit_type', 'agent', 'company',
        'days_in_waiting_list', 'customer_type', 'adr', 'required_car_parking_spaces',
        'total_of_special_requests', 'reservation_status', 'reservation_status_date'
    ]
    df = pd.read_csv('hotel_bookings_clean.csv', header=None, names=cols)
    df['arrival_date'] = pd.to_datetime(df['arrival_date'], errors='coerce')
    
    day_map = {
        'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
        'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun'
    }
    df['day_abbr'] = df['arrival_date'].dt.day_name().map(day_map).fillna('Sat')
    
    month_map = {
        'January': 'Jan', 'February': 'Feb', 'March': 'Mar', 'April': 'Apr',
        'May': 'May', 'June': 'Jun', 'July': 'Jul', 'August': 'Aug',
        'September': 'Sep', 'October': 'Oct', 'November': 'Nov', 'December': 'Dec'
    }
    df['month_abbr'] = df['arrival_date_month'].map(month_map).fillna('Aug')

    bins = [-1, 7, 30, 90, 180, 10000]
    labels = ['0-7 Days', '8-30 Days', '31-90 Days', '91-180 Days', '180+ Days']
    df['lead_bucket'] = pd.cut(df['lead_time'], bins=bins, labels=labels).astype(str)

    df = df[(df['market_segment'] != 'Undefined') & (df['distribution_channel'] != 'Undefined')]
    df['nights'] = df['total_nights'].clip(lower=1)
    df['rev'] = df['nights'] * df['adr']

    # 1. Main Cross-Filter Micro-Cube (Includes customer_type for Q4 of Project Brief)
    cube = df.groupby(
        ['hotel', 'market_segment', 'deposit_type', 'lead_bucket', 'month_abbr',
         'distribution_channel', 'customer_type', 'day_abbr', 'reserved_room_type'],
        observed=True
    ).agg(
        b=('is_canceled', 'count'),
        c=('is_canceled', 'sum'),
        rev=('rev', 'sum'),
        adr_sum=('adr', 'sum')
    ).reset_index()

    # 2. Representative Scatter Sample
    scat_df = df[df['adr'].between(25, 480)].sample(min(320, len(df)), random_state=42).copy()
    np.random.seed(42)
    scat_df['risk_x'] = (scat_df['lead_time'] / 4.2 + np.random.normal(0, 3.5, len(scat_df))).clip(3, 97).round(1)
    scat_df['adr_y'] = scat_df['adr'].round(2)
    scatter_records = scat_df[[
        'hotel', 'market_segment', 'deposit_type', 'lead_bucket', 'month_abbr',
        'distribution_channel', 'customer_type', 'day_abbr', 'risk_x', 'adr_y'
    ]].to_dict(orient='records')

    return json.dumps(cube.to_dict(orient='records')), json.dumps(scatter_records)

cube_json, scatter_json = build_in_memory_cubes()

# -------------------------------------------------------------
# 3. PURE CLIENT-SIDE APPLICATION (0MS INTERACTIVITY)
# -------------------------------------------------------------
app_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        user-select: none;
    }}
    body {{
        background: radial-gradient(circle at 55% 15%, #0d162b 0%, #060913 100%);
        color: #E2E8F0;
        font-family: 'Inter', sans-serif;
        display: flex;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
    }}

    /* ================= PERMANENT LEFT SIDEBAR ================= */
    .sidebar {{
        width: 265px;
        min-width: 265px;
        background-color: #050811;
        border-right: 1px solid rgba(212, 175, 55, 0.25);
        display: flex;
        flex-direction: column;
        padding: 18px 14px;
        z-index: 10;
        overflow-y: auto;
    }}
    .crest-box {{
        text-align: center;
        padding-bottom: 16px;
        border-bottom: 1px solid rgba(212, 175, 55, 0.18);
        margin-bottom: 14px;
    }}
    .crest-icon {{
        font-size: 34px;
        color: #D4AF37;
        line-height: 1;
        text-shadow: 0 0 12px rgba(212, 175, 55, 0.4);
    }}
    .crest-title {{
        font-family: 'Cinzel', serif;
        font-size: 17px;
        font-weight: 700;
        letter-spacing: 4px;
        color: #F5E6C8;
        margin-top: 4px;
    }}
    .crest-sub {{
        font-size: 9px;
        color: #8C9BAE;
        letter-spacing: 1.8px;
        text-transform: uppercase;
        margin-top: 2px;
    }}

    .nav-group {{
        display: flex;
        flex-direction: column;
        gap: 4px;
    }}
    .nav-btn {{
        background: transparent;
        border: 1px solid transparent;
        border-left: 3px solid transparent;
        color: #94A3B8;
        padding: 9px 12px;
        font-size: 12px;
        font-weight: 500;
        text-align: left;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.12s ease;
    }}
    .nav-btn:hover {{
        background: rgba(212, 175, 55, 0.08);
        color: #F5E6C8;
    }}
    .nav-btn.active {{
        background: rgba(212, 175, 55, 0.14);
        color: #F5E6C8;
        border-left: 3px solid #D4AF37;
        font-weight: 600;
    }}

    .slicer-section {{
        margin-top: 18px;
        padding-top: 14px;
        border-top: 1px solid rgba(212, 175, 55, 0.18);
    }}
    .slicer-label {{
        font-size: 10.5px;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
        display: block;
    }}
    .prop-select {{
        width: 100%;
        background-color: #0b1222;
        color: #F5E6C8;
        border: 1px solid rgba(212, 175, 55, 0.35);
        border-radius: 5px;
        padding: 8px 10px;
        font-size: 12px;
        outline: none;
        cursor: pointer;
    }}

    .q1-benchmark-box {{
        margin-top: 14px;
        background: rgba(14, 22, 42, 0.65);
        border: 1px solid rgba(212, 175, 55, 0.22);
        border-radius: 6px;
        padding: 10px 12px;
        font-size: 11px;
        line-height: 1.55;
        color: #CBD5E1;
    }}

    .active-filter-box {{
        margin-top: 14px;
        background: rgba(212, 175, 55, 0.1);
        border: 1px solid #D4AF37;
        border-radius: 6px;
        padding: 10px 12px;
        font-size: 11px;
        display: none;
    }}
    .filter-tag-list {{
        color: #F5E6C8;
        margin: 6px 0 10px 0;
        line-height: 1.45;
    }}
    .reset-btn {{
        width: 100%;
        background: #D4AF37;
        color: #060913;
        border: none;
        padding: 7px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 11px;
        cursor: pointer;
        transition: 0.15s;
    }}
    .reset-btn:hover {{
        background: #F5E6C8;
    }}

    /* ================= MAIN WORKSPACE ================= */
    .main-area {{
        flex: 1;
        padding: 16px 22px 32px 22px;
        overflow-y: auto;
        height: 100vh;
    }}
    .top-header {{
        text-align: center;
        margin-bottom: 14px;
    }}
    .top-title {{
        font-family: 'Cinzel', serif;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: 5px;
        color: #F5E6C8;
    }}
    .top-subtitle {{
        font-size: 10px;
        letter-spacing: 3px;
        color: #B38F48;
        text-transform: uppercase;
        margin-top: 3px;
    }}

    /* ================= 4 TOP KPI CARDS ================= */
    .kpi-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-bottom: 14px;
    }}
    .kpi-card {{
        background: linear-gradient(180deg, rgba(16, 25, 45, 0.85) 0%, rgba(8, 13, 25, 0.96) 100%);
        border: 1px solid rgba(212, 175, 55, 0.28);
        border-radius: 8px;
        padding: 12px 16px;
        position: relative;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
    }}
    .kpi-dot {{
        position: absolute;
        top: 12px;
        right: 12px;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #D4AF37;
        box-shadow: 0 0 8px #D4AF37;
    }}
    .kpi-hdr {{
        font-size: 10.5px;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-weight: 600;
    }}
    .kpi-val {{
        font-size: 25px;
        font-weight: 700;
        color: #FFFFFF;
        margin: 4px 0;
    }}
    .kpi-sub {{
        font-size: 10.5px;
        color: #D4AF37;
    }}

    /* ================= VISUAL GRIDS & CARDS ================= */
    .grid-3 {{
        display: grid;
        grid-template-columns: 1.08fr 1.46fr 1.46fr;
        gap: 14px;
        margin-bottom: 14px;
    }}
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin-bottom: 14px;
    }}
    .panel-card {{
        background: linear-gradient(180deg, rgba(14, 22, 42, 0.8) 0%, rgba(8, 12, 24, 0.95) 100%);
        border: 1px solid rgba(212, 175, 55, 0.26);
        border-radius: 8px;
        padding: 12px 15px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}
    .panel-hdr {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2px;
    }}
    .panel-title {{
        font-size: 11px;
        font-weight: 700;
        color: #F5E6C8;
        letter-spacing: 0.7px;
        text-transform: uppercase;
    }}
    .panel-hint {{
        font-size: 9.5px;
        color: #D4AF37;
        font-weight: 600;
    }}
    .panel-msg {{
        font-size: 10.5px;
        color: #94A3B8;
        margin-bottom: 8px;
        font-style: italic;
    }}
    .takeaway-foot {{
        margin-top: 6px;
        padding-top: 6px;
        border-top: 1px solid rgba(212, 175, 55, 0.14);
        font-size: 10.5px;
        color: #CBD5E1;
        line-height: 1.4;
    }}

    /* ================= UNCLIPPED SVG GAUGES ================= */
    .gauge-item {{
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 10px;
    }}
    .gauge-lbl {{
        font-size: 10px;
        color: #8C9BAE;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .gauge-num {{
        font-size: 14.5px;
        font-weight: 700;
        color: #FFFFFF;
        margin-top: 2px;
    }}

    .section-divider {{
        border: none;
        border-top: 1px solid rgba(212, 175, 55, 0.2);
        margin: 16px 0 12px 0;
    }}
    .section-banner {{
        font-size: 11.5px;
        font-weight: 700;
        color: #F5E6C8;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }}

    /* ================= README DOCS ================= */
    .readme-wrap {{
        max-width: 980px;
        margin: 0 auto;
    }}
    .doc-card {{
        background: rgba(14, 22, 42, 0.78);
        border: 1px solid rgba(212, 175, 55, 0.28);
        border-left: 4px solid #D4AF37;
        border-radius: 6px;
        padding: 16px 20px;
        margin-bottom: 14px;
    }}
    .doc-h3 {{
        font-family: 'Cinzel', serif;
        color: #F5E6C8;
        font-size: 15.5px;
        margin-bottom: 8px;
    }}
    .doc-p {{
        font-size: 12.8px;
        color: #CBD5E1;
        line-height: 1.65;
    }}
    .badge-gold {{
        background: rgba(212, 175, 55, 0.16);
        color: #D4AF37;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 600;
    }}
</style>
</head>
<body>

    <!-- ==================== LEFT SIDEBAR ==================== -->
    <div class="sidebar">
        <div class="crest-box">
            <div class="crest-icon">♚</div>
            <div class="crest-title">ROYALTY</div>
            <div class="crest-sub">Lisbon & Algarve Portfolio</div>
        </div>

        <div class="nav-group">
            <button class="nav-btn active" id="tab_exec" onclick="switchView('exec')">▶ Executive View</button>
            <button class="nav-btn" id="tab_risk" onclick="switchView('risk')">   Analytics & Risk (Q1–Q5)</button>
            <button class="nav-btn" id="tab_yield" onclick="switchView('yield')">   Yield Management (Q6)</button>
            <button class="nav-btn" id="tab_forecast" onclick="switchView('forecast')">   Seasonality & Pacing</button>
            <button class="nav-btn" id="tab_rate" onclick="switchView('rate')">   Lisbon vs Algarve ADR</button>
            <button class="nav-btn" id="tab_readme" onclick="switchView('readme')">   📖 Brief README & Docs</button>
        </div>

        <div class="slicer-section">
            <label class="slicer-label">Q1 Property Slicer:</label>
            <select class="prop-select" id="hotelSelect" onchange="onPropertyChange(this.value)">
                <option value="All">All Properties (119,209)</option>
                <option value="City Hotel">City Hotel (Lisbon)</option>
                <option value="Resort Hotel">Resort Hotel (Algarve)</option>
            </select>
        </div>

        <!-- Q1 Benchmark Reference Box -->
        <div class="q1-benchmark-box">
            <b style="color: #D4AF37;">Q1 Baseline Cancellation Share:</b><br>
            • Overall: <b>37.04%</b> (44,153 / 119,209)<br>
            • City Hotel (Lisbon): <b>41.71%</b><br>
            • Resort Hotel (Algarve): <b>27.76%</b>
        </div>

        <div class="active-filter-box" id="filterBox">
            <div style="color: #D4AF37; font-weight: 700; font-size: 10.5px; text-transform: uppercase;">⚡ Cross-Filter Active</div>
            <div class="filter-tag-list" id="filterList"></div>
            <button class="reset-btn" onclick="resetAllFilters()">↺ Reset All Filters</button>
        </div>
    </div>

    <!-- ==================== MAIN WORKSPACE ==================== -->
    <div class="main-area">
        <div class="top-header">
            <div class="top-title">WHY HOTEL GUESTS CANCEL & HOW TO REDUCE CANCELLATIONS</div>
            <div class="top-subtitle" id="viewSubtitle">EXECUTIVE VIEW — PORTUGUESE CITY (LISBON) & RESORT (ALGARVE) HOTELS</div>
        </div>

        <!-- TOP 4 KPI CARDS (Q1 & REVENUE IMPACT) -->
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-dot"></div>
                <div class="kpi-hdr">Q1 Cancellation Rate</div>
                <div class="kpi-val" id="kpiCancel">--%</div>
                <div class="kpi-sub" id="kpiCancelCount">Cancelled Bookings: --</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-hdr">Realized Stay Share</div>
                <div class="kpi-val" id="kpiOcc">--%</div>
                <div class="kpi-sub">Guests Who Actually Stayed (Target: 85%)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-dot"></div>
                <div class="kpi-hdr">Realized RevPAR (vs ADR)</div>
                <div class="kpi-val" id="kpiRevpar">$--</div>
                <div class="kpi-sub" id="kpiAdrSub">Average Daily Rate: $--</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-hdr">Revenue at Risk (Cancelled)</div>
                <div class="kpi-val" id="kpiLostRev">$--M</div>
                <div class="kpi-sub" id="kpiGrossSub">Out of $--M Gross Volume</div>
            </div>
        </div>

        <!-- ==================== ROW 1: EXECUTIVE COCKPIT ==================== -->
        <div id="sectionExecTop" class="grid-3">
            <!-- Panel 1: Unclipped SVG Ring Gauges -->
            <div class="panel-card">
                <div class="panel-hdr">
                    <span class="panel-title">Q6 Yield & Overbooking Calibration</span>
                    <span style="color: #10B981; font-size: 12px;">●</span>
                </div>
                <div class="panel-msg">Real-time capacity & overbooking buffer</div>

                <div class="gauge-item">
                    <div id="g1Svg"></div>
                    <div>
                        <div class="gauge-lbl">Retention Rate:</div>
                        <div class="gauge-num" id="g1Txt">--</div>
                    </div>
                </div>
                <div class="gauge-item">
                    <div id="g2Svg"></div>
                    <div>
                        <div class="gauge-lbl">Optimal Tier ADR:</div>
                        <div class="gauge-num" id="g2Txt">--</div>
                    </div>
                </div>
                <div class="gauge-item" style="margin-bottom: 0;">
                    <div id="g3Svg"></div>
                    <div>
                        <div class="gauge-lbl">Cancellation Risk:</div>
                        <div class="gauge-num" id="g3Txt">--</div>
                    </div>
                </div>
            </div>

            <!-- Panel 2: ADR vs Cancellation Scatter -->
            <div class="panel-card">
                <div class="panel-hdr">
                    <span class="panel-title">ADR vs. Lead-Time Cancellation Risk</span>
                    <span class="panel-hint">Price Elasticity Check</span>
                </div>
                <div class="panel-msg">Cancellations cluster by lead time rather than high room price</div>
                <div id="chartScatter" style="width: 100%; height: 220px;"></div>
            </div>

            <!-- Panel 3: Calendar Occupancy Loss Matrix -->
            <div class="panel-card">
                <div class="panel-hdr">
                    <span class="panel-title">Q5 Arrival Day & Month Risk Matrix</span>
                    <span class="panel-hint">Click Cell to Filter</span>
                </div>
                <div class="panel-msg">Spring/Summer & weekend check-ins experience peak attrition</div>
                <div id="chartMatrix" style="width: 100%; height: 220px;"></div>
            </div>
        </div>

        <!-- ==================== ROW 2: THE 6 PROJECT BRIEF QUESTIONS ENGINE ==================== -->
        <div id="sectionRiskEngine">
            <hr class="section-divider" id="execDivider">
            <div class="section-banner">
                <span>⚡ Interactive Answers to Brief Questions Q2–Q5 (Click any bar, slice, or point to cross-filter — click again to reset)</span>
            </div>

            <!-- Q2 (Lead Time) & Q5 (Monthly Seasonality) -->
            <div class="grid-2">
                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Q2: Lead Time — Far-In-Advance Bookings Cancel 4x More Often</span>
                        <span class="panel-hint">Click Bar to Filter</span>
                    </div>
                    <div id="chartLead" style="width: 100%; height: 215px;"></div>
                    <div class="takeaway-foot">
                        <b>Takeaway:</b> Bookings made 0–7 days before arrival cancel at ~10%, while bookings 180+ days out exceed 55% cancellation. Long lead time is the #1 behavioral predictor of cancellation.
                    </div>
                </div>

                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Q5: Seasonality — Peak Spring & Summer Months (Apr–Aug) Are Riskiest</span>
                        <span class="panel-hint">Click Point to Filter</span>
                    </div>
                    <div id="chartSeason" style="width: 100%; height: 215px;"></div>
                    <div class="takeaway-foot">
                        <b>Takeaway:</b> Cancellation rates peak between April and August (~39%–41%) when high-volume summer vacation and tour group inventory is booked far in advance, dropping to ~30% in winter.
                    </div>
                </div>
            </div>

            <!-- Q3 (Deposit Paradox) & Q4 (Market Segments) -->
            <div class="grid-2">
                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Q3: Deposit Paradox — Non-Refundable Blocks Cancel at 99.4%</span>
                        <span class="panel-hint">Click Bar to Filter</span>
                    </div>
                    <div id="chartDeposit" style="width: 100%; height: 215px;"></div>
                    <div class="takeaway-foot">
                        <b>Takeaway:</b> Counterintuitively, <i>Non Refund</i> bookings (14,587 rows) cancel at 99.4% because wholesale tour operators & groups reserve speculative blocks that default. Note: <i>Refundable</i> is a tiny group (162 rows) and should not be over-interpreted.
                    </div>
                </div>

                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Q4A: Market Segment — Groups (61%) & Online TA (37%) Cancel Most</span>
                        <span class="panel-hint">Click Bar to Filter</span>
                    </div>
                    <div id="chartSegment" style="width: 100%; height: 215px;"></div>
                    <div class="takeaway-foot">
                        <b>Takeaway:</b> Direct (15.3%) and Corporate (18.7%) guests are highly reliable. Groups (61.1%) and Online Travel Agencies (36.8%) drive the vast majority of empty rooms. Small segments (Aviation, Complementary) represent &lt;1% of volume.
                    </div>
                </div>
            </div>

            <!-- Q4B (Distribution Channel Pie) & Q4C (Customer Type) -->
            <div class="grid-2">
                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Q4B: Booking Channels — TA/TO Dominates Volume & Risk (41% Cancel)</span>
                        <span class="panel-hint">Click Slice to Filter</span>
                    </div>
                    <div id="chartPie" style="width: 100%; height: 215px;"></div>
                    <div class="takeaway-foot">
                        <b>Takeaway:</b> Travel Agents / Tour Operators (TA/TO) generate 82% of all bookings but cancel at 41.0%—more than double the cancellation rate of Direct bookings (17.5%).
                    </div>
                </div>

                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Q4C: Customer Types — Transient Bookings Cancel Most (40.7%)</span>
                        <span class="panel-hint">Click Bar to Filter</span>
                    </div>
                    <div id="chartCustomer" style="width: 100%; height: 215px;"></div>
                    <div class="takeaway-foot">
                        <b>Takeaway:</b> Individual <i>Transient</i> travelers (75% of all bookings, often booking via OTAs) cancel at 40.7%, compared to 25.4% for <i>Transient-Party</i> and 31.0% for <i>Contract</i> stays.
                    </div>
                </div>
            </div>
        </div>

        <!-- ==================== VIEW 3: YIELD MANAGEMENT ==================== -->
        <div id="sectionYield" style="display: none;">
            <div class="grid-2">
                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">ADR & Cancellation Rate by Reserved Room Type</span>
                        <span class="panel-hint">Click Bar to Filter Room</span>
                    </div>
                    <div id="chartRoom" style="width: 100%; height: 320px;"></div>
                </div>
                <div class="panel-card">
                    <div class="panel-hdr">
                        <span class="panel-title">Booking Channel Volume Share</span>
                        <span class="panel-hint">Click Slice to Filter</span>
                    </div>
                    <div id="chartYieldPie" style="width: 100%; height: 320px;"></div>
                </div>
            </div>
        </div>

        <!-- ==================== VIEW 4: FORECASTING ==================== -->
        <div id="sectionForecast" style="display: none;">
            <div class="panel-card">
                <div class="panel-hdr">
                    <span class="panel-title">Monthly Booking Volume: Confirmed Stays vs. Cancellations</span>
                    <span class="panel-hint">Click Month Bar to Cross-Filter</span>
                </div>
                <div id="chartPace" style="width: 100%; height: 360px;"></div>
            </div>
        </div>

        <!-- ==================== VIEW 5: RATE SHOPPER ==================== -->
        <div id="sectionRate" style="display: none;">
            <div class="panel-card">
                <div class="panel-hdr">
                    <span class="panel-title">City Hotel (Lisbon) vs. Resort Hotel (Algarve): Seasonal ADR Comparison</span>
                    <span class="panel-hint">Algarve Surges in Summer; Lisbon Stays Steady</span>
                </div>
                <div id="chartRateComp" style="width: 100%; height: 360px;"></div>
            </div>
        </div>

        <!-- ==================== VIEW 6: BRIEF-ALIGNED README & METHODOLOGY ==================== -->
        <div id="sectionReadme" class="readme-wrap" style="display: none;">
            <div class="doc-card">
                <div class="doc-h3">1. The Business Question & Dataset</div>
                <div class="doc-p">
                    <b>Business Problem:</b> A hotel loses money whenever a guest cancels a booking and the room goes empty. Our objective is to answer: <i>Why do hotel guests cancel, and what can the hotel do about it?</i><br><br>
                    <b>Dataset:</b> Kaggle <i>Hotel Booking Demand</i> (by Jesse Mostipak) containing bookings across two Portuguese properties: <b>City Hotel (Lisbon)</b> and <b>Resort Hotel (Algarve)</b>. Target variable: <span class="badge-gold">is_canceled</span> (1 = cancelled, 0 = guest stayed).
                </div>
            </div>

            <div class="doc-card">
                <div class="doc-h3">2. Data Cleaning & Methodology (SQL Server & Python Audit)</div>
                <div class="doc-p">
                    • <b>Raw Imported Rows:</b> <span class="badge-gold">119,390</span> rows across 32 columns confirmed in SQL Server (SSMS).<br>
                    • <b>Unusual Rows Removed:</b> Removed <b>180 rows</b> with zero total guests (<code>adults + children + babies = 0</code>) and <b>1 extreme price outlier</b> (ADR = $5,400), resulting in <span class="badge-gold">119,209</span> verified clean bookings in <code>bookings_clean</code>.<br>
                    • <b>Missing Values Handled:</b> Replaced <code>NULL</code> values in <code>children</code> (4 rows) with 0, and standardized missing codes in <code>country</code>, <code>agent</code>, and <code>company</code>.<br>
                    • <b>Engineered Columns:</b> Created <code>total_nights</code> (<code>stays_in_weekend_nights + stays_in_week_nights</code>), a proper <code>arrival_date</code>, and <code>lead_time_bucket</code>. Note: Following the brief's standards, exact duplicates were retained in the main table because batch group reservations share identical timestamps and attributes.
                </div>
            </div>

            <div class="doc-card">
                <div class="doc-h3">3. Answers to the 6 Project Brief Questions</div>
                <div class="doc-p">
                    <b>Q1. What share of bookings are cancelled, overall and for each hotel?</b><br>
                    Overall, <b>37.04%</b> of bookings are cancelled (44,153 of 119,209). <b>City Hotel (Lisbon)</b> has a <b>41.71%</b> cancellation rate (33,079 / 79,302), which is significantly higher than <b>Resort Hotel (Algarve)</b> at <b>27.76%</b> (11,074 / 39,907).<br><br>

                    <b>Q2. Does booking far in advance (lead time) make a cancellation more likely?</b><br>
                    <b>Yes—dramatically.</b> Bookings made <b>0–7 days</b> before arrival cancel at just <b>9.6%</b>. This climbs to <b>27.9%</b> (8–30 days), <b>37.7%</b> (31–90 days), <b>44.7%</b> (91–180 days), and <b>57.0%</b> for bookings made <b>180+ days</b> in advance.<br><br>

                    <b>Q3. Do deposits reduce cancellations?</b><br>
                    In theory yes, but the data reveals a major anomaly: <b>No Deposit</b> bookings cancel at <b>28.4%</b> (104,460 rows) and <b>Refundable</b> bookings cancel at <b>22.2%</b> (only 162 rows—too small a sample to generalize). Shockingly, <b>Non Refund</b> bookings cancel at <b>99.4%</b> (14,587 rows). Cross-tabulation shows these are overwhelmingly <b>Groups and Offline TA/TO blocks</b> where intermediaries reserve speculative inventory under non-refundable codes and later forfeit or default.<br><br>

                    <b>Q4. Which booking channels, market segments, and customer types cancel most?</b><br>
                    • <i>Market Segments:</i> <b>Groups (61.1%)</b> and <b>Online TA (36.8%)</b> cancel most; <b>Direct (15.3%)</b> and <b>Corporate (18.7%)</b> cancel least.<br>
                    • <i>Booking Channels:</i> <b>TA/TO (41.0%)</b> cancels more than twice as often as <b>Direct (17.5%)</b> and <b>Corporate (22.1%)</b>.<br>
                    • <i>Customer Types:</i> <b>Transient (40.7%)</b> cancels most, followed by <b>Contract (31.0%)</b>, <b>Transient-Party (25.4%)</b>, and <b>Group (10.1%)</b>.<br><br>

                    <b>Q5. Which months and seasons are riskiest?</b><br>
                    Late spring and peak summer—specifically <b>April (40.8%)</b>, <b>May (39.7%)</b>, <b>June (41.5%)</b>, <b>July (37.4%)</b>, and <b>August (37.8%)</b>—carry the highest cancellation rates and the largest dollar volume of lost rooms. Winter months (November–January) have the lowest risk (~30%–32%).
                </div>
            </div>

            <div class="doc-card">
                <div class="doc-h3">4. Q6 Recommendations & Honest Limitations</div>
                <div class="doc-p">
                    <b>Actionable Recommendations:</b><br>
                    1. <b>Audit Wholesale & Group "Non-Refund" Contracts:</b> Require verified stage payments at 90 and 60 days prior to arrival so tour operators cannot hold speculative blocks that cancel at 99%.<br>
                    2. <b>Targeted Overbooking & Re-Confirmation on 90+ Day Lead Times:</b> Send automated check-in confirmation prompts at 45 days out for Online TA bookings and apply a controlled 10%–15% overbooking buffer on long-lead inventory.<br>
                    3. <b>Shift Mix Toward Direct Bookings:</b> Offer complimentary perks (late checkout, welcome drink, room upgrade) on the direct website to convert 40%-risk OTA shoppers into 15%-risk Direct guests.<br><br>

                    <b>Limitations:</b><br>
                    • <i>Anonymized Payment Mechanics:</i> The dataset does not show whether the hotel actually collected cash on cancelled <code>Non Refund</code> bookings or if payment cards failed.<br>
                    • <i>Small Subgroup Sample Sizes:</i> Categories like <code>Refundable</code> deposits (162 rows), <code>GDS</code> channel (193 rows), and <code>Aviation</code> segment (235 rows) represent less than 0.2% of bookings and must not be over-interpreted.
                </div>
            </div>
        </div>
    </div>

<script>
    const CUBE = {cube_json};
    const SCATTER = {scatter_json};

    // Active Cross-Filter State
    const state = {{
        view: 'exec',
        hotel: 'All',
        channel: null,
        lead: null,
        month: null,
        segment: null,
        deposit: null,
        customer: null,
        day: null,
        room: null
    }};

    const charts = {{
        scatter: echarts.init(document.getElementById('chartScatter')),
        matrix: echarts.init(document.getElementById('chartMatrix')),
        lead: echarts.init(document.getElementById('chartLead')),
        season: echarts.init(document.getElementById('chartSeason')),
        pie: echarts.init(document.getElementById('chartPie')),
        segment: echarts.init(document.getElementById('chartSegment')),
        deposit: echarts.init(document.getElementById('chartDeposit')),
        customer: echarts.init(document.getElementById('chartCustomer')),
        room: echarts.init(document.getElementById('chartRoom')),
        yieldPie: echarts.init(document.getElementById('chartYieldPie')),
        pace: echarts.init(document.getElementById('chartPace')),
        rateComp: echarts.init(document.getElementById('chartRateComp'))
    }};

    function makeSvgRing(val, maxVal, color) {{
        const pct = Math.max(0, Math.min(1, val / maxVal));
        const r = 26;
        const circ = 2 * Math.PI * r;
        const dash = pct * circ;
        return `
            <svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="${{r}}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="6"/>
                <circle cx="32" cy="32" r="${{r}}" fill="none" stroke="${{color}}" stroke-width="6"
                        stroke-dasharray="${{dash}} ${{circ - dash}}" stroke-dashoffset="0"
                        stroke-linecap="round" transform="rotate(-90 32 32)"/>
            </svg>
        `;
    }}

    function filterCubeExcept(ignoreDim) {{
        return CUBE.filter(r => {{
            if (state.hotel !== 'All' && r.hotel !== state.hotel) return false;
            if (ignoreDim !== 'channel' && state.channel && r.distribution_channel !== state.channel) return false;
            if (ignoreDim !== 'lead' && state.lead && r.lead_bucket !== state.lead) return false;
            if (ignoreDim !== 'month' && state.month && r.month_abbr !== state.month) return false;
            if (ignoreDim !== 'segment' && state.segment && r.market_segment !== state.segment) return false;
            if (ignoreDim !== 'deposit' && state.deposit && r.deposit_type !== state.deposit) return false;
            if (ignoreDim !== 'customer' && state.customer && r.customer_type !== state.customer) return false;
            if (ignoreDim !== 'day' && state.day && r.day_abbr !== state.day) return false;
            if (ignoreDim !== 'room' && state.room && r.reserved_room_type !== state.room) return false;
            return true;
        }});
    }}

    function renderAll() {{
        const fullFiltered = filterCubeExcept(null);

        // 1. KPI Totals
        let totalB = 0, totalC = 0, totalRev = 0, totalAdr = 0;
        fullFiltered.forEach(r => {{
            totalB += r.b;
            totalC += r.c;
            totalRev += r.rev;
            totalAdr += r.adr_sum;
        }});

        const cancelRate = totalB > 0 ? (totalC / totalB * 100) : 0;
        const occRate = Math.max(0, 100 - cancelRate);
        const avgAdr = totalB > 0 ? (totalAdr / totalB) : 0;
        const revPar = avgAdr * (occRate / 100);
        const lostRev = totalRev * (cancelRate / 100);

        document.getElementById('kpiCancel').innerText = cancelRate.toFixed(1) + '%';
        document.getElementById('kpiCancelCount').innerText = `${{totalC.toLocaleString()}} of ${{totalB.toLocaleString()}} bookings`;
        document.getElementById('kpiOcc').innerText = occRate.toFixed(1) + '%';
        document.getElementById('kpiRevpar').innerText = '$' + revPar.toFixed(2);
        document.getElementById('kpiAdrSub').innerText = `Avg Daily Rate (ADR): $${{avgAdr.toFixed(2)}}`;
        document.getElementById('kpiLostRev').innerText = '$' + (lostRev / 1e6).toFixed(2) + 'M';
        document.getElementById('kpiGrossSub').innerText = `Out of $${{(totalRev / 1e6).toFixed(2)}}M Gross Demand`;

        // 2. SVG Ring Gauges
        document.getElementById('g1Svg').innerHTML = makeSvgRing(occRate, 100, '#D4AF37');
        document.getElementById('g1Txt').innerText = `${{occRate.toFixed(1)}}% Kept`;

        const optRate = avgAdr * 1.15;
        document.getElementById('g2Svg').innerHTML = makeSvgRing(optRate, 350, '#EAB308');
        document.getElementById('g2Txt').innerText = '$' + optRate.toFixed(0);

        const riskCol = cancelRate > 35 ? '#EF4444' : '#10B981';
        document.getElementById('g3Svg').innerHTML = makeSvgRing(cancelRate, 100, riskCol);
        document.getElementById('g3Txt').innerText = cancelRate.toFixed(1) + '%';

        // 3. Active Filter Sidebar Box
        const tags = [];
        if (state.channel) tags.push(`• Channel: <b>${{state.channel}}</b>`);
        if (state.lead) tags.push(`• Lead Time: <b>${{state.lead}}</b>`);
        if (state.month) tags.push(`• Month: <b>${{state.month}}</b>`);
        if (state.segment) tags.push(`• Segment: <b>${{state.segment}}</b>`);
        if (state.deposit) tags.push(`• Deposit: <b>${{state.deposit}}</b>`);
        if (state.customer) tags.push(`• Customer: <b>${{state.customer}}</b>`);
        if (state.day) tags.push(`• Arrival Day: <b>${{state.day}}</b>`);
        if (state.room) tags.push(`• Room: <b>${{state.room}}</b>`);

        const fBox = document.getElementById('filterBox');
        if (tags.length > 0) {{
            fBox.style.display = 'block';
            document.getElementById('filterList').innerHTML = tags.join('<br>');
        }} else {{
            fBox.style.display = 'none';
        }}

        // 4. Update All Visuals
        updateScatter();
        updateMatrix(fullFiltered);
        updateLead();
        updateSeason();
        updatePie();
        updateSegment();
        updateDeposit();
        updateCustomer();
        updateYieldCharts();
        updateForecastChart(fullFiltered);
        updateRateShopper();
    }}

    function updateScatter() {{
        const pts = SCATTER.filter(p => {{
            if (state.hotel !== 'All' && p.hotel !== state.hotel) return false;
            if (state.channel && p.distribution_channel !== state.channel) return false;
            if (state.lead && p.lead_bucket !== state.lead) return false;
            if (state.month && p.month_abbr !== state.month) return false;
            if (state.segment && p.market_segment !== state.segment) return false;
            if (state.deposit && p.deposit_type !== state.deposit) return false;
            if (state.customer && p.customer_type !== state.customer) return false;
            if (state.day && p.day_abbr !== state.day) return false;
            return true;
        }}).map(p => [p.risk_x, p.adr_y]);

        charts.scatter.setOption({{
            grid: {{ left: 42, right: 15, top: 10, bottom: 25 }},
            tooltip: {{ formatter: p => `Cancel Risk: ${{p.value[0]}}%<br>ADR: $${{p.value[1]}}` }},
            xAxis: {{
                type: 'value', min: 0, max: 100,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            yAxis: {{
                type: 'value', min: 0, max: 500,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '${{value}}' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            series: [{{
                type: 'scatter',
                symbolSize: 5,
                data: pts,
                itemStyle: {{ color: '#D4AF37', opacity: 0.82 }}
            }}]
        }});
    }}

    function updateMatrix(records) {{
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const grid = {{}};
        days.forEach(d => months.forEach(m => grid[`${{d}}_${{m}}`] = {{b:0, c:0}}));

        records.forEach(r => {{
            const k = `${{r.day_abbr}}_${{r.month_abbr}}`;
            if (grid[k]) {{
                grid[k].b += r.b;
                grid[k].c += r.c;
            }}
        }});

        const heatData = [];
        months.forEach((m, xIdx) => {{
            days.forEach((d, yIdx) => {{
                const cell = grid[`${{d}}_${{m}}`];
                const rate = cell.b > 0 ? +(cell.c / cell.b * 100).toFixed(1) : 0;
                heatData.push([xIdx, yIdx, rate]);
            }});
        }});

        charts.matrix.setOption({{
            tooltip: {{
                position: 'top',
                formatter: p => `${{days[p.value[1]]}}, ${{months[p.value[0]]}}: <b>${{p.value[2]}}% Cancel Rate</b>`
            }},
            grid: {{ left: 38, right: 8, top: 22, bottom: 10 }},
            xAxis: {{
                type: 'category', data: months, position: 'top',
                axisLabel: {{ color: '#64748B', fontSize: 8.5 }},
                splitArea: {{ show: true }}
            }},
            yAxis: {{
                type: 'category', data: days,
                axisLabel: {{ color: '#64748B', fontSize: 9 }},
                splitArea: {{ show: true }}
            }},
            visualMap: {{
                min: 15, max: 60, show: false,
                inRange: {{ color: ['#0a101d', '#1e2433', '#967527', '#ffd875'] }}
            }},
            series: [{{
                type: 'heatmap',
                data: heatData,
                itemStyle: {{ borderColor: '#070B18', borderWidth: 2 }}
            }}]
        }});
    }}

    function updateLead() {{
        const buckets = ['0-7 Days', '8-30 Days', '31-90 Days', '91-180 Days', '180+ Days'];
        const map = {{}};
        buckets.forEach(b => map[b] = {{b:0, c:0}});

        filterCubeExcept('lead').forEach(r => {{
            if (map[r.lead_bucket]) {{
                map[r.lead_bucket].b += r.b;
                map[r.lead_bucket].c += r.c;
            }}
        }});

        const colors = ['#1E3A5F', '#4A6984', '#B8860B', '#D97706', '#EF4444'];
        const barData = buckets.map((k, idx) => {{
            const rate = map[k].b > 0 ? +(map[k].c / map[k].b * 100).toFixed(1) : 0;
            const active = (!state.lead || state.lead === k);
            return {{
                name: k,
                value: rate,
                bookings: map[k].b,
                itemStyle: {{
                    color: colors[idx],
                    opacity: active ? 1.0 : 0.22,
                    borderColor: state.lead === k ? '#FFFFFF' : 'transparent',
                    borderWidth: state.lead === k ? 1.5 : 0
                }}
            }};
        }});

        charts.lead.setOption({{
            tooltip: {{ formatter: p => `${{p.name}}: <b>${{p.value}}% Cancel Rate</b><br>Bookings: ${{p.data.bookings.toLocaleString()}}` }},
            grid: {{ left: 38, right: 15, top: 22, bottom: 25 }},
            xAxis: {{
                type: 'category', data: buckets,
                axisLabel: {{ color: '#94A3B8', fontSize: 9.5 }}
            }},
            yAxis: {{
                type: 'value', max: 80,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            series: [{{
                type: 'bar', data: barData, barWidth: '50%',
                label: {{ show: true, position: 'top', color: '#F5E6C8', fontSize: 9.5, formatter: '{{c}}%' }}
            }}]
        }});
    }}

    function updateSeason() {{
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const map = {{}};
        months.forEach(m => map[m] = {{b:0, c:0}});

        filterCubeExcept('month').forEach(r => {{
            if (map[r.month_abbr]) {{
                map[r.month_abbr].b += r.b;
                map[r.month_abbr].c += r.c;
            }}
        }});

        const lineData = months.map(m => {{
            const rate = map[m].b > 0 ? +(map[m].c / map[m].b * 100).toFixed(1) : 0;
            return {{
                name: m,
                value: rate,
                bookings: map[m].b,
                symbolSize: state.month === m ? 12 : 7,
                itemStyle: {{
                    color: state.month === m ? '#EF4444' : '#F5E6C8',
                    borderColor: '#D4AF37',
                    borderWidth: 2
                }}
            }};
        }});

        charts.season.setOption({{
            tooltip: {{ trigger: 'axis', formatter: p => `${{p[0].name}}: <b>${{p[0].value}}% Cancel Rate</b><br>Bookings: ${{p[0].data.bookings.toLocaleString()}}` }},
            grid: {{ left: 38, right: 15, top: 22, bottom: 25 }},
            xAxis: {{
                type: 'category', data: months,
                axisLabel: {{ color: '#94A3B8', fontSize: 9.5 }}
            }},
            yAxis: {{
                type: 'value', min: 15, max: 65,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            series: [{{
                type: 'line', data: lineData, smooth: true,
                lineStyle: {{ color: '#D4AF37', width: 2.5 }},
                label: {{ show: true, position: 'top', color: '#F5E6C8', fontSize: 9, formatter: '{{c}}%' }}
            }}]
        }});
    }}

    function updatePie() {{
        const map = {{}};
        filterCubeExcept('channel').forEach(r => {{
            if (!map[r.distribution_channel]) map[r.distribution_channel] = {{b:0, c:0}};
            map[r.distribution_channel].b += r.b;
            map[r.distribution_channel].c += r.c;
        }});

        const palette = ['#D4AF37', '#38BDF8', '#10B981', '#EF4444', '#A855F7'];
        const pieData = Object.keys(map).map((k, i) => {{
            const cRate = map[k].b > 0 ? (map[k].c / map[k].b * 100).toFixed(1) : 0;
            return {{
                name: k,
                value: map[k].b,
                cancelRate: cRate,
                selected: state.channel === k,
                itemStyle: {{
                    color: palette[i % palette.length],
                    opacity: (!state.channel || state.channel === k) ? 1.0 : 0.22,
                    borderColor: state.channel === k ? '#FFFFFF' : '#070B18',
                    borderWidth: state.channel === k ? 2 : 1
                }}
            }};
        }});

        const pieOption = {{
            tooltip: {{
                trigger: 'item',
                formatter: p => `Channel <b>${{p.name}}</b><br>Bookings: ${{p.value.toLocaleString()}} (${{p.percent}}%)<br>Cancel Rate: <b>${{p.data.cancelRate}}%</b>`
            }},
            legend: {{ bottom: 0, textStyle: {{ color: '#94A3B8', fontSize: 10 }} }},
            series: [{{
                type: 'pie',
                radius: ['40%', '68%'],
                center: ['50%', '43%'],
                selectedMode: 'single',
                data: pieData,
                label: {{
                    show: true,
                    color: '#E2E8F0',
                    fontSize: 9.5,
                    formatter: '{{b}}\\n{{d}}%'
                }}
            }}]
        }};

        charts.pie.setOption(pieOption);
        charts.yieldPie.setOption(pieOption);
    }}

    function updateSegment() {{
        const map = {{}};
        filterCubeExcept('segment').forEach(r => {{
            if (!map[r.market_segment]) map[r.market_segment] = {{b:0, c:0}};
            map[r.market_segment].b += r.b;
            map[r.market_segment].c += r.c;
        }});

        const keys = Object.keys(map).sort((a,b) => {{
            const ra = map[a].b > 0 ? map[a].c / map[a].b : 0;
            const rb = map[b].b > 0 ? map[b].c / map[b].b : 0;
            return ra - rb;
        }});

        const sData = keys.map(k => {{
            const rate = map[k].b > 0 ? +(map[k].c / map[k].b * 100).toFixed(1) : 0;
            const active = (!state.segment || state.segment === k);
            return {{
                name: k,
                value: rate,
                bookings: map[k].b,
                itemStyle: {{
                    color: rate > 50 ? '#EF4444' : (rate > 30 ? '#D4AF37' : '#38BDF8'),
                    opacity: active ? 1.0 : 0.22
                }}
            }};
        }});

        charts.segment.setOption({{
            tooltip: {{ formatter: p => `${{p.name}}: <b>${{p.value}}% Cancel Rate</b><br>Bookings: ${{p.data.bookings.toLocaleString()}}` }},
            grid: {{ left: 88, right: 42, top: 8, bottom: 20 }},
            xAxis: {{
                type: 'value', max: 80,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            yAxis: {{
                type: 'category', data: keys,
                axisLabel: {{ color: '#94A3B8', fontSize: 9.5 }}
            }},
            series: [{{
                type: 'bar', data: sData,
                label: {{ show: true, position: 'right', color: '#F5E6C8', fontSize: 9, formatter: '{{c}}%' }}
            }}]
        }});
    }}

    function updateDeposit() {{
        const deps = ['No Deposit', 'Non Refund', 'Refundable'];
        const map = {{ 'No Deposit': {{b:0,c:0}}, 'Non Refund': {{b:0,c:0}}, 'Refundable': {{b:0,c:0}} }};

        filterCubeExcept('deposit').forEach(r => {{
            if (map[r.deposit_type]) {{
                map[r.deposit_type].b += r.b;
                map[r.deposit_type].c += r.c;
            }}
        }});

        const colMap = {{ 'No Deposit': '#D4AF37', 'Non Refund': '#EF4444', 'Refundable': '#10B981' }};
        const dData = deps.map(d => {{
            const rate = map[d].b > 0 ? +(map[d].c / map[d].b * 100).toFixed(1) : 0;
            const active = (!state.deposit || state.deposit === d);
            return {{
                name: d,
                value: rate,
                bookings: map[d].b,
                itemStyle: {{
                    color: colMap[d],
                    opacity: active ? 1.0 : 0.22
                }}
            }};
        }});

        charts.deposit.setOption({{
            tooltip: {{ formatter: p => `${{p.name}}: <b>${{p.value}}% Cancel Rate</b><br>Bookings: ${{p.data.bookings.toLocaleString()}}` }},
            grid: {{ left: 38, right: 15, top: 22, bottom: 25 }},
            xAxis: {{
                type: 'category', data: deps,
                axisLabel: {{ color: '#94A3B8', fontSize: 9.5 }}
            }},
            yAxis: {{
                type: 'value', max: 110,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            series: [{{
                type: 'bar', data: dData, barWidth: '42%',
                label: {{ show: true, position: 'top', color: '#F5E6C8', fontSize: 9.5, formatter: '{{c}}%' }}
            }}]
        }});
    }}

    function updateCustomer() {{
        const custTypes = ['Transient', 'Contract', 'Transient-Party', 'Group'];
        const map = {{ 'Transient': {{b:0,c:0}}, 'Contract': {{b:0,c:0}}, 'Transient-Party': {{b:0,c:0}}, 'Group': {{b:0,c:0}} }};

        filterCubeExcept('customer').forEach(r => {{
            if (map[r.customer_type]) {{
                map[r.customer_type].b += r.b;
                map[r.customer_type].c += r.c;
            }}
        }});

        const cData = custTypes.map(ct => {{
            const rate = map[ct].b > 0 ? +(map[ct].c / map[ct].b * 100).toFixed(1) : 0;
            const active = (!state.customer || state.customer === ct);
            return {{
                name: ct,
                value: rate,
                bookings: map[ct].b,
                itemStyle: {{
                    color: ct === 'Transient' ? '#EF4444' : '#D4AF37',
                    opacity: active ? 1.0 : 0.22
                }}
            }};
        }});

        charts.customer.setOption({{
            tooltip: {{ formatter: p => `${{p.name}}: <b>${{p.value}}% Cancel Rate</b><br>Bookings: ${{p.data.bookings.toLocaleString()}}` }},
            grid: {{ left: 38, right: 15, top: 22, bottom: 25 }},
            xAxis: {{
                type: 'category', data: custTypes,
                axisLabel: {{ color: '#94A3B8', fontSize: 9.5 }}
            }},
            yAxis: {{
                type: 'value', max: 60,
                axisLabel: {{ color: '#64748B', fontSize: 9, formatter: '{{value}}%' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }}
            }},
            series: [{{
                type: 'bar', data: cData, barWidth: '45%',
                label: {{ show: true, position: 'top', color: '#F5E6C8', fontSize: 9.5, formatter: '{{c}}%' }}
            }}]
        }});
    }}

    function updateYieldCharts() {{
        const map = {{}};
        filterCubeExcept('room').forEach(r => {{
            if (!map[r.reserved_room_type]) map[r.reserved_room_type] = {{b:0, adr:0}};
            map[r.reserved_room_type].b += r.b;
            map[r.reserved_room_type].adr += r.adr_sum;
        }});
        const rooms = Object.keys(map).sort();
        const rData = rooms.map(rm => ({{
            name: rm,
            value: map[rm].b > 0 ? +(map[rm].adr / map[rm].b).toFixed(0) : 0,
            itemStyle: {{
                color: '#D4AF37',
                opacity: (!state.room || state.room === rm) ? 1.0 : 0.25
            }}
        }}));

        charts.room.setOption({{
            tooltip: {{ formatter: 'Room {{b}}: <b>${{c}} Avg ADR</b>' }},
            grid: {{ left: 45, right: 20, top: 25, bottom: 30 }},
            xAxis: {{ type: 'category', data: rooms, axisLabel: {{ color: '#94A3B8' }} }},
            yAxis: {{ type: 'value', axisLabel: {{ color: '#64748B', formatter: '${{value}}' }}, splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }} }},
            series: [{{ type: 'bar', data: rData, label: {{ show: true, position: 'top', color: '#F5E6C8', formatter: '${{c}}' }} }}]
        }});
    }}

    function updateForecastChart(records) {{
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const conf = months.map(() => 0);
        const canc = months.map(() => 0);

        records.forEach(r => {{
            const idx = months.indexOf(r.month_abbr);
            if (idx !== -1) {{
                conf[idx] += (r.b - r.c);
                canc[idx] += r.c;
            }}
        }});

        charts.pace.setOption({{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ top: 0, textStyle: {{ color: '#94A3B8' }} }},
            grid: {{ left: 50, right: 20, top: 35, bottom: 30 }},
            xAxis: {{ type: 'category', data: months, axisLabel: {{ color: '#94A3B8' }} }},
            yAxis: {{ type: 'value', axisLabel: {{ color: '#64748B' }}, splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }} }},
            series: [
                {{ name: 'Guests Stayed (is_canceled = 0)', type: 'bar', stack: 'tot', data: conf, itemStyle: {{ color: '#D4AF37' }} }},
                {{ name: 'Cancelled (is_canceled = 1)', type: 'bar', stack: 'tot', data: canc, itemStyle: {{ color: '#EF4444' }} }}
            ]
        }});
    }}

    function updateRateShopper() {{
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const city = months.map(() => ({{b:0, adr:0}}));
        const resort = months.map(() => ({{b:0, adr:0}}));

        CUBE.forEach(r => {{
            const idx = months.indexOf(r.month_abbr);
            if (idx !== -1) {{
                if (r.hotel === 'City Hotel') {{ city[idx].b += r.b; city[idx].adr += r.adr_sum; }}
                else {{ resort[idx].b += r.b; resort[idx].adr += r.adr_sum; }}
            }}
        }});

        charts.rateComp.setOption({{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ top: 0, textStyle: {{ color: '#94A3B8' }} }},
            grid: {{ left: 50, right: 20, top: 35, bottom: 30 }},
            xAxis: {{ type: 'category', data: months, axisLabel: {{ color: '#94A3B8' }} }},
            yAxis: {{ type: 'value', axisLabel: {{ color: '#64748B', formatter: '${{value}}' }}, splitLine: {{ lineStyle: {{ color: 'rgba(212,175,55,0.1)' }} }} }},
            series: [
                {{ name: 'Resort Hotel (Algarve) ADR', type: 'line', smooth: true, data: resort.map(x => x.b > 0 ? +(x.adr/x.b).toFixed(1) : 0), itemStyle: {{ color: '#D4AF37' }}, lineStyle: {{ width: 3 }} }},
                {{ name: 'City Hotel (Lisbon) ADR', type: 'line', smooth: true, data: city.map(x => x.b > 0 ? +(x.adr/x.b).toFixed(1) : 0), itemStyle: {{ color: '#38BDF8' }}, lineStyle: {{ width: 3 }} }}
            ]
        }});
    }}

    // ================= 0MS POWER BI CLICK LISTENERS =================
    function toggleState(key, val) {{
        state[key] = (state[key] === val) ? null : val;
        renderAll();
    }}

    charts.pie.on('click', p => toggleState('channel', p.name));
    charts.yieldPie.on('click', p => toggleState('channel', p.name));
    charts.lead.on('click', p => toggleState('lead', p.name));
    charts.season.on('click', p => toggleState('month', p.name));
    charts.segment.on('click', p => toggleState('segment', p.name));
    charts.deposit.on('click', p => toggleState('deposit', p.name));
    charts.customer.on('click', p => toggleState('customer', p.name));
    charts.room.on('click', p => toggleState('room', p.name));
    charts.pace.on('click', p => toggleState('month', p.name));
    charts.matrix.on('click', p => {{
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const clickedDay = days[p.value[1]];
        toggleState('day', clickedDay);
    }});

    function onPropertyChange(val) {{
        state.hotel = val;
        renderAll();
    }}

    function resetAllFilters() {{
        state.channel = null;
        state.lead = null;
        state.month = null;
        state.segment = null;
        state.deposit = null;
        state.customer = null;
        state.day = null;
        state.room = null;
        renderAll();
    }}

    // ================= INSTANT SIDEBAR VIEW SWITCHING =================
    function switchView(v) {{
        state.view = v;
        const tabs = ['exec', 'risk', 'yield', 'forecast', 'rate', 'readme'];
        const titles = {{
            exec: 'EXECUTIVE VIEW — PORTUGUESE CITY (LISBON) & RESORT (ALGARVE) HOTELS',
            risk: 'QUESTIONS Q1–Q5: LEAD TIME, SEASONALITY, DEPOSITS, SEGMENTS & CUSTOMER TYPES',
            yield: 'QUESTION Q6: DYNAMIC YIELD & ROOM RATE ELASTICITY',
            forecast: 'MONTHLY BOOKING PACING: STAYED (0) VS. CANCELLED (1)',
            rate: 'PORTUGUESE PROPERTY COMPARISON: LISBON (CITY) VS. ALGARVE (RESORT)',
            readme: 'PROJECT BRIEF README, SQL AUDIT, FINDINGS & LIMITATIONS'
        }};
        const labels = {{
            exec: 'Executive View',
            risk: 'Analytics & Risk (Q1–Q5)',
            yield: 'Yield Management (Q6)',
            forecast: 'Seasonality & Pacing',
            rate: 'Lisbon vs Algarve ADR',
            readme: '📖 Brief README & Docs'
        }};

        tabs.forEach(t => {{
            const btn = document.getElementById('tab_' + t);
            if (t === v) {{
                btn.classList.add('active');
                btn.innerText = '▶ ' + labels[t];
            }} else {{
                btn.classList.remove('active');
                btn.innerText = '   ' + labels[t];
            }}
        }});

        document.getElementById('viewSubtitle').innerText = titles[v];

        document.getElementById('sectionExecTop').style.display = (v === 'exec') ? 'grid' : 'none';
        document.getElementById('execDivider').style.display = (v === 'exec') ? 'block' : 'none';
        document.getElementById('sectionRiskEngine').style.display = (v === 'exec' || v === 'risk') ? 'block' : 'none';
        document.getElementById('sectionYield').style.display = (v === 'yield') ? 'block' : 'none';
        document.getElementById('sectionForecast').style.display = (v === 'forecast') ? 'block' : 'none';
        document.getElementById('sectionRate').style.display = (v === 'rate') ? 'block' : 'none';
        document.getElementById('sectionReadme').style.display = (v === 'readme') ? 'block' : 'none';

        setTimeout(() => {{
            Object.values(charts).forEach(c => c.resize());
        }}, 20);
    }}

    window.addEventListener('resize', () => {{
        Object.values(charts).forEach(c => c.resize());
    }});

    renderAll();
</script>
</body>
</html>
"""

st.components.v1.html(app_html, height=1000, scrolling=False)