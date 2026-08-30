import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from django.conf import settings
from .models import Event
import matplotlib
matplotlib.use('Agg') # For headless plotting

def load_dataframe():
    # Explicitly filter and pull only events with status='Completed'
    events = Event.objects.filter(status='Completed').values(
        'id', 'name', 'event_type', 'department', 'academic_year', 'event_date',
        'registrations', 'attendance', 'completion', 'feedback_rating', 'feedback_responses'
    )
    df = pd.DataFrame(list(events))
    return df

def validate(df):
    if df.empty:
        df['is_valid'] = pd.Series(dtype=bool)
        df['data_issue'] = pd.Series(dtype=str)
        return df
        
    df['is_valid'] = True
    df['data_issue'] = ""
    
    # Flag (never silently drop) rows where attendance > registrations or completion > attendance
    mask1 = df['attendance'] > df['registrations']
    mask2 = df['completion'] > df['attendance']
    
    df.loc[mask1, 'is_valid'] = False
    df.loc[mask1, 'data_issue'] = "Attendance > Registrations"
    
    df.loc[mask2, 'is_valid'] = False
    df.loc[mask2, 'data_issue'] = "Completion > Attendance"
    
    mask3 = mask1 & mask2
    df.loc[mask3, 'data_issue'] = "Attendance > Registrations & Completion > Attendance"
    
    return df

def add_metrics(df):
    if df.empty:
        df['conversion_rate'] = pd.Series(dtype=float)
        df['completion_rate'] = pd.Series(dtype=float)
        return df
        
    # conversion_rate = attendance/registrations*100 (NaN if registrations==0)
    df['conversion_rate'] = np.where(df['registrations'] == 0, np.nan, (df['attendance'] / df['registrations']) * 100)
    
    # completion_rate = completion/attendance*100 (NaN if attendance==0 or completion is null)
    df['completion_rate'] = np.where(
        (df['attendance'] == 0) | df['completion'].isna(), 
        np.nan, 
        (df['completion'] / df['attendance']) * 100
    )
    return df

def add_reliability_tier(df):
    if df.empty:
        df['feedback_tier'] = pd.Series(dtype=str)
        return df
        
    # Bin feedback_responses into No Data (0), Insufficient Evidence (1-4), Low Confidence (5-19), Moderate Confidence (20-49), High Confidence (50+)
    # using pd.cut with bins=[-1,0,4,19,49,inf]
    labels = ['No Data', 'Insufficient Evidence', 'Low Confidence', 'Moderate Confidence', 'High Confidence']
    df['feedback_tier'] = pd.cut(df['feedback_responses'], bins=[-1, 0, 4, 19, 49, np.inf], labels=labels)
    df['feedback_tier'] = df['feedback_tier'].astype(str)
    return df

def add_score(df):
    if df.empty:
        df['score'] = pd.Series(dtype=float)
        return df
        
    # Normalize components 0-1
    max_att = df.loc[df['is_valid'], 'attendance'].max() if 'is_valid' in df.columns else df['attendance'].max()
    att_norm = df['attendance'] / max_att if pd.notna(max_att) and max_att > 0 else 0
    
    conv_norm = df['conversion_rate'] / 100
    comp_norm = df['completion_rate'] / 100
    fb_norm = (df['feedback_rating'] - 1) / 4
    
    # participation_score = average of normalized attendance + normalized conversion
    part_score = (att_norm + conv_norm) / 2
    
    # final score = equal average of participation_score, completion_norm, feedback_norm
    score_components = pd.DataFrame({
        'part': part_score,
        'comp': comp_norm,
        'fb': fb_norm
    })
    
    # Multiply by 100 for a 0-100 scale output
    df['score'] = score_components.mean(axis=1) * 100 
    
    # Only score rows where is_valid is True and feedback_tier is not 'No Data'
    mask = df['is_valid'] & (df['feedback_tier'] != 'No Data')
    df.loc[~mask, 'score'] = np.nan
    
    return df

def add_insights(df):
    if df.empty:
        df['headline_insight'] = pd.Series(dtype=str)
        df['low_reliability_tag'] = pd.Series(dtype=bool)
        return df
        
    def get_group_stats(group_df):
        return pd.Series({
            'score_90': group_df['score'].quantile(0.9) if not group_df['score'].dropna().empty else np.nan,
            'fb_75': group_df['feedback_rating'].quantile(0.75) if not group_df['feedback_rating'].dropna().empty else np.nan,
            'fb_25': group_df['feedback_rating'].quantile(0.25) if not group_df['feedback_rating'].dropna().empty else np.nan,
            'att_75': group_df['attendance'].quantile(0.75) if not group_df['attendance'].dropna().empty else np.nan,
            'att_25': group_df['attendance'].quantile(0.25) if not group_df['attendance'].dropna().empty else np.nan,
        })
        
    global_stats = get_group_stats(df)
    
    type_stats = {}
    for ev_type, group in df.groupby('event_type'):
        if len(group) >= 4:
            type_stats[ev_type] = get_group_stats(group)
        else:
            type_stats[ev_type] = global_stats

    df['headline_insight'] = ""
    df['low_reliability_tag'] = False

    for idx, row in df.iterrows():
        stats = type_stats.get(row['event_type'], global_stats)
        
        insight = ""
        
        # 1. Data Quality Issue
        if not row['is_valid']:
            insight = "Data Quality Issue"
        
        # 2. Exceptional Score
        elif pd.notna(row['score']) and pd.notna(global_stats['score_90']) and row['score'] >= global_stats['score_90'] and row['feedback_tier'] not in ['No Data', 'Insufficient Evidence']:
            insight = "Exceptional Score"
            
        # 3. High Quality / Low Reach
        elif (pd.notna(row['feedback_rating']) and pd.notna(stats['fb_75']) and row['feedback_rating'] >= stats['fb_75']) and \
             (pd.notna(row['attendance']) and pd.notna(stats['att_25']) and row['attendance'] <= stats['att_25']):
            insight = "High Quality / Low Reach"
            
        # 4. High Reach / Low Satisfaction (inverse)
        elif (pd.notna(row['attendance']) and pd.notna(stats['att_75']) and row['attendance'] >= stats['att_75']) and \
             (pd.notna(row['feedback_rating']) and pd.notna(stats['fb_25']) and row['feedback_rating'] <= stats['fb_25']):
            insight = "High Reach / Low Satisfaction"
            
        # 5. No-show Alert
        elif pd.notna(row['conversion_rate']) and row['conversion_rate'] < 30:
            insight = "No-show Alert"
            
        # 6. Strong Completion
        elif pd.notna(row['completion_rate']) and row['completion_rate'] > 90:
            insight = "Strong Completion"
            
        df.at[idx, 'headline_insight'] = insight
        
        # Separately attach a Low Reliability tag
        if row['feedback_tier'] in ['Insufficient Evidence', 'Low Confidence']:
            df.at[idx, 'low_reliability_tag'] = True

    return df

def make_charts(df):
    img_dir = settings.MEDIA_ROOT
    os.makedirs(img_dir, exist_ok=True)
    
    chart_paths = {}
    if df.empty:
        return chart_paths

    # 1. Department participation bar chart
    dept_df = df.groupby('department')['attendance'].sum().reset_index()
    plt.figure(figsize=(8, 5))
    plt.bar(dept_df['department'], dept_df['attendance'], color='skyblue')
    plt.title('Total Attendance by Department')
    plt.xlabel('Department')
    plt.ylabel('Total Attendance')
    if df['low_reliability_tag'].any():
        plt.figtext(0.99, 0.01, '* Note: Some data points represent low-reliability feedback', ha='right', fontsize=8, color='red')
    path_dept = os.path.join(img_dir, 'dept_participation.png')
    plt.tight_layout()
    plt.savefig(path_dept)
    plt.close()
    chart_paths['dept_participation'] = 'dept_participation.png'
    
    # 2. Conversion rate sorted bar chart (grouped by event type for readability)
    type_conv = df.groupby('event_type')['conversion_rate'].mean().sort_values(ascending=False).reset_index()
    plt.figure(figsize=(8, 5))
    plt.bar(type_conv['event_type'], type_conv['conversion_rate'], color='lightgreen')
    plt.title('Average Conversion Rate by Event Type')
    plt.xlabel('Event Type')
    plt.ylabel('Conversion Rate (%)')
    if df['low_reliability_tag'].any():
        plt.figtext(0.99, 0.01, '* Note: Some data points represent low-reliability feedback', ha='right', fontsize=8, color='red')
    path_conv = os.path.join(img_dir, 'conversion_rates.png')
    plt.tight_layout()
    plt.savefig(path_conv)
    plt.close()
    chart_paths['conversion_rates'] = 'conversion_rates.png'
    
    # 3. Quality-vs-reach scatter
    plt.figure(figsize=(8, 5))
    high_rel = df[~df['low_reliability_tag']]
    low_rel = df[df['low_reliability_tag']]
    
    plt.scatter(high_rel['attendance'], high_rel['feedback_rating'], color='blue', label='Reliable', alpha=0.7)
    plt.scatter(low_rel['attendance'], low_rel['feedback_rating'], color='red', label='Low Reliability', alpha=0.5, marker='x')
    
    plt.title('Quality vs Reach')
    plt.xlabel('Attendance')
    plt.ylabel('Feedback Rating')
    plt.legend()
    if df['low_reliability_tag'].any():
        plt.figtext(0.99, 0.01, '* Red "x" markers represent low-reliability feedback', ha='right', fontsize=8, color='red')
    
    path_scatter = os.path.join(img_dir, 'quality_vs_reach.png')
    plt.tight_layout()
    plt.savefig(path_scatter)
    plt.close()
    chart_paths['quality_vs_reach'] = 'quality_vs_reach.png'
    
    return chart_paths

def compute_dashboard():
    df = load_dataframe()
    df = validate(df)
    df = add_metrics(df)
    df = add_reliability_tier(df)
    df = add_score(df)
    df = add_insights(df)
    
    kpis = {
        'total_events': len(df),
        'total_registrations': int(df['registrations'].sum()) if not df.empty else 0,
        'total_attendance': int(df['attendance'].sum()) if not df.empty else 0,
        'overall_conversion': round((df['attendance'].sum() / df['registrations'].sum() * 100), 2) if not df.empty and df['registrations'].sum() > 0 else 0,
        'average_feedback': round(df['feedback_rating'].mean(), 2) if not df.empty and pd.notna(df['feedback_rating'].mean()) else 0
    }
    
    if not df.empty:
        valid_df = df[df['is_valid']].copy()
        valid_df = valid_df.sort_values(by='score', ascending=False, na_position='last')
        ranked_events = valid_df.to_dict('records')
        
        dept_summary = df.groupby('department').agg(
            events=('id', 'count'),
            avg_attendance=('attendance', 'mean'),
            avg_feedback=('feedback_rating', 'mean')
        ).reset_index().to_dict('records')

        type_summary = df.groupby('event_type').agg(
            events=('id', 'count'),
            avg_attendance=('attendance', 'mean'),
            avg_feedback=('feedback_rating', 'mean')
        ).reset_index().to_dict('records')

        year_summary = df.groupby('academic_year').agg(
            events=('id', 'count'),
            avg_attendance=('attendance', 'mean'),
            avg_feedback=('feedback_rating', 'mean')
        ).reset_index().to_dict('records')
        
        # Replace NaNs with None for easier serialization in templates
        for event in ranked_events:
            for k, v in event.items():
                if pd.isna(v):
                    event[k] = None
        
        for summary in [dept_summary, type_summary, year_summary]:
            for row in summary:
                for k, v in row.items():
                    if pd.isna(v):
                        row[k] = None

        warnings = df[(df['low_reliability_tag'] == True) | (df['is_valid'] == False)][
            ['name', 'feedback_tier', 'data_issue', 'low_reliability_tag', 'is_valid']
        ].to_dict('records')
    else:
        ranked_events = []
        dept_summary = []
        type_summary = []
        year_summary = []
        warnings = []
        
    chart_paths = make_charts(df)
    
    return {
        'kpis': kpis,
        'ranked_events': ranked_events,
        'department_summary': dept_summary,
        'event_type_summary': type_summary,
        'academic_year_summary': year_summary,
        'warnings': warnings,
        'chart_paths': chart_paths
    }
