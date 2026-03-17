import streamlit as st
import pandas as pd
import re

st.set_page_config(layout="wide", page_title="Blinn Schedule Builder Turbo")

# --- HELPER FUNCTIONS ---
def time_to_minutes(time_str):
    if not time_str or pd.isna(time_str) or str(time_str).upper() == 'TBA':
        return None
    time_str = str(time_str).lower().strip()
    match = re.search(r'(\d+):(\d+)\s*(am|pm)', time_str)
    if not match: return None
    hours, minutes, period = match.groups()
    hours, minutes = int(hours), int(minutes)
    if period == 'pm' and hours != 12: hours += 12
    if period == 'am' and hours == 12: hours = 0
    return (hours * 60) + minutes

def minutes_to_time_str(m):
    h, min = m // 60, m % 60
    period = "AM" if h < 12 else "PM"
    h_display = h if h <= 12 else h - 12
    if h_display == 0: h_display = 12
    return f"{h_display}:{min:02d} {period}"

# --- DATA LOADING (OPTIMIZED) ---
@st.cache_data
def load_data():
    df = pd.read_csv('output.csv', dtype={'CRN': str, 'Course Number': str, 'Section': str})
    
    # Metadata healing
    metadata_cols = ['Title', 'Part of Term', 'Co-enroll', 'Attributes', 'Subject', 
                     'Course Number', 'Section', 'Campus', 'Type', 'Method', 'Credits']
    for col in metadata_cols:
        if col in df.columns:
            df[col] = df.groupby('CRN')[col].transform(lambda x: x.ffill().bfill())

    df['Attributes'] = df['Attributes'].fillna('')
    df['Campus'] = df['Campus'].fillna('Unknown')
    df['Subject'] = df['Subject'].fillna('')
    df['Co-enroll'] = df['Co-enroll'].fillna('').astype(str).replace('nan', '')
    df['start_min'] = df['Start Time'].apply(time_to_minutes)
    df['end_min'] = df['End Time'].apply(time_to_minutes)
    
    # PRE-CALCULATE FOOTPRINTS
    # Create a dictionary where key is CRN and value is a list of all meeting times
    # This avoids doing df[df['CRN'] == row['CRN']] thousands of times
    footprint_map = {}
    for crn, group in df.groupby('CRN'):
        times = []
        for _, row in group.iterrows():
            if not pd.isna(row['start_min']):
                times.append({'start': row['start_min'], 'end': row['end_min'], 'days': set(str(row['Days']))})
        footprint_map[crn] = times
        
    return df, footprint_map

df, footprint_map = load_data()

# --- SESSION STATE ---
if 'my_schedule' not in st.session_state:
    st.session_state.my_schedule = []

# --- SIDEBAR FILTERS ---
st.sidebar.header("Search Filters")
all_subjects = sorted([s for s in df['Subject'].unique() if s])
sel_subjects = st.sidebar.multiselect("Subjects", all_subjects)

all_campuses = sorted(df['Campus'].unique())
sel_campus = st.sidebar.multiselect("Campus", all_campuses, default=all_campuses)

only_coenroll = st.sidebar.toggle("Show Only Co-enrollment Required", value=False)
hide_conflicts = st.sidebar.toggle("Hide Conflicting Classes", value=True)

st.sidebar.subheader("Time Range Preference")
start_limit = st.sidebar.slider("Start Time No Earlier Than", 420, 1320, 420, step=30)
end_limit = st.sidebar.slider("End Time No Later Than", 420, 1320, 1320, step=30)

# --- TURBO FILTERING LOGIC ---
f_df = df[df['Campus'].isin(sel_campus)]
if sel_subjects:
    f_df = f_df[f_df['Subject'].isin(sel_subjects)]
if only_coenroll:
    f_df = f_df[f_df['Co-enroll'] != '']

# Optimized check
active_schedule_times = []
for crn in st.session_state.my_schedule:
    active_schedule_times.extend(footprint_map.get(crn, []))

def turbo_check(row):
    crn = row['CRN']
    partner_crn = row['Co-enroll']
    
    # Get all times for this group (self + partner)
    check_times = footprint_map.get(crn, []).copy()
    if partner_crn and partner_crn in footprint_map:
        check_times.extend(footprint_map[partner_crn])
    
    for t in check_times:
        # Time Filter Check
        if t['start'] < start_limit or t['end'] > end_limit:
            return False
            
        # Conflict Check
        if hide_conflicts:
            for s in active_schedule_times:
                if t['days'].intersection(s['days']):
                    if not (t['end'] < s['start'] or s['end'] < t['start']):
                        return False
    return True

if not f_df.empty:
    mask = f_df.apply(turbo_check, axis=1)
    f_df = f_df[mask]

# --- MAIN UI ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Results ({len(f_df)} sections)")
    display_df = f_df[['Title', 'Subject', 'Course Number', 'Section', 'CRN', 'Days', 'Start Time', 'End Time', 'Co-enroll']]
    
    event = st.dataframe(display_df, width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row")

    if len(event.selection.rows) > 0:
        selected_row = f_df.iloc[event.selection.rows[0]]
        crn = selected_row['CRN']
        if st.button(f"Add CRN {crn}"):
            for c in [crn, selected_row['Co-enroll']]:
                if c and c != '' and c not in st.session_state.my_schedule:
                    st.session_state.my_schedule.append(c)
            st.rerun()

with col2:
    st.subheader("My Schedule")
    if not st.session_state.my_schedule:
        st.write("No classes selected.")
    else:
        my_df = df[df['CRN'].isin(st.session_state.my_schedule)].drop_duplicates('CRN')
        remove_event = st.dataframe(my_df[['Subject', 'Course Number', 'CRN', 'Days', 'Start Time']], 
                                    width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row", key="remove_table")
        
        if len(remove_event.selection.rows) > 0:
            selected_idx = remove_event.selection.rows[0]
            if selected_idx < len(my_df):
                row_to_remove = my_df.iloc[selected_idx]
                if st.button(f"Remove CRN {row_to_remove['CRN']}"):
                    st.session_state.my_schedule = [c for c in st.session_state.my_schedule if c != row_to_remove['CRN'] and c != row_to_remove['Co-enroll']]
                    st.rerun()

        if st.button("Clear All"):
            st.session_state.my_schedule = []
            st.rerun()