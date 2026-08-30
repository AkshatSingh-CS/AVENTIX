import pandas as pd
import numpy as np
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from .models import Event
from .analytics import add_metrics, add_reliability_tier, add_score, add_insights

class EventModelTests(TestCase):
    def test_attendance_greater_than_registrations_fails(self):
        event = Event(
            name="Test", event_type=Event.EventType.WORKSHOP, department=Event.Department.CS,
            academic_year=Event.AcademicYear.YEAR_2023_2024, event_date=date(2023, 9, 1),
            status=Event.Status.PLANNED, registrations=10, attendance=15
        )
        with self.assertRaises(ValidationError) as context:
            event.clean()
        self.assertIn('attendance', context.exception.error_dict)

class AnalyticsLogicTests(TestCase):
    def test_zero_denominator_metrics(self):
        df = pd.DataFrame([{
            'registrations': 0,
            'attendance': 0,
            'completion': 0
        }])
        df = add_metrics(df)
        self.assertTrue(pd.isna(df.iloc[0]['conversion_rate']))
        self.assertTrue(pd.isna(df.iloc[0]['completion_rate']))

    def test_reliability_tier_boundaries(self):
        df = pd.DataFrame({
            'feedback_responses': [0, 1, 4, 5, 19, 20, 49, 50]
        })
        df = add_reliability_tier(df)
        tiers = df['feedback_tier'].tolist()
        expected = [
            'No Data',                # 0
            'Insufficient Evidence',  # 1
            'Insufficient Evidence',  # 4
            'Low Confidence',         # 5
            'Low Confidence',         # 19
            'Moderate Confidence',    # 20
            'Moderate Confidence',    # 49
            'High Confidence'         # 50
        ]
        self.assertEqual(tiers, expected)

    def test_score_calculation(self):
        # Score calculation confirms attendance is NOT double-counted
        df = pd.DataFrame([{
            'is_valid': True,
            'feedback_tier': 'High Confidence',
            'attendance': 50,
            'conversion_rate': 50.0,
            'completion_rate': 100.0,
            'feedback_rating': 3.0
        }, {
            'is_valid': True,
            'feedback_tier': 'High Confidence',
            'attendance': 100, # to set max_att=100
            'conversion_rate': 100.0,
            'completion_rate': 100.0,
            'feedback_rating': 5.0
        }])
        df = add_score(df)
        score1 = df.iloc[0]['score']
        score2 = df.iloc[1]['score']
        # Event 1: att_norm=0.5, conv_norm=0.5 => part_score=0.5. comp_norm=1.0, fb_norm=0.5. Average = 2.0 / 3 = 0.6666...
        self.assertAlmostEqual(score1, 66.66666666666667)
        # Event 2: att_norm=1.0, conv_norm=1.0 => part_score=1.0. comp_norm=1.0, fb_norm=1.0. Average = 3.0 / 3 = 1.0
        self.assertAlmostEqual(score2, 100.0)

    def test_insight_engine_priority(self):
        # We will create an event that matches 3+ rules: 
        # is_valid=False (1), No-show Alert (5), Strong Completion (6)
        # We add a dummy event to ensure the target event doesn't trigger "Exceptional Score"
        # by making sure the target score (10.0) is not in the top decile.
        df = pd.DataFrame([{
            'event_type': 'Workshop',
            'is_valid': False,
            'score': 10.0,
            'feedback_rating': 2.0,
            'attendance': 10,
            'conversion_rate': 10.0,
            'completion_rate': 100.0,
            'feedback_tier': 'High Confidence'
        }, {
            'event_type': 'Workshop',
            'is_valid': True,
            'score': 100.0,
            'feedback_rating': 5.0,
            'attendance': 100,
            'conversion_rate': 100.0,
            'completion_rate': 100.0,
            'feedback_tier': 'High Confidence'
        }])
        
        df = add_insights(df)
        # priority 1 wins for the first event
        self.assertEqual(df.iloc[0]['headline_insight'], 'Data Quality Issue')
        
        # Now let's make it valid. It should trigger No-show Alert (5) before Strong Completion (6)
        df.loc[0, 'is_valid'] = True
        df = add_insights(df)
        self.assertEqual(df.iloc[0]['headline_insight'], 'No-show Alert')
        
        # Fix conversion_rate, now should trigger Strong Completion (6)
        df.loc[0, 'conversion_rate'] = 50.0
        df = add_insights(df)
        self.assertEqual(df.iloc[0]['headline_insight'], 'Strong Completion')

    def test_max_attendance_ignores_invalid(self):
        df = pd.DataFrame([{
            'is_valid': True,
            'feedback_tier': 'High Confidence',
            'attendance': 50,
            'conversion_rate': 100.0,
            'completion_rate': 100.0,
            'feedback_rating': 5.0
        }, {
            'is_valid': False,
            'feedback_tier': 'High Confidence',
            'attendance': 1000, # A very large attendance that should be ignored
            'conversion_rate': 100.0,
            'completion_rate': 100.0,
            'feedback_rating': 5.0
        }])
        df = add_score(df)
        
        # Valid event should be normalized against its own attendance (max=50), so att_norm = 1.0
        # participation_score = (1.0 + 1.0)/2 = 1.0
        # final_score = (1.0 + 1.0 + 1.0)/3 * 100 = 100.0
        self.assertAlmostEqual(df.iloc[0]['score'], 100.0)
        self.assertTrue(pd.isna(df.iloc[1]['score']))
