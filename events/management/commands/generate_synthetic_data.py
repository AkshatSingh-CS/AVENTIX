from django.core.management.base import BaseCommand
from events.models import Event
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Generates 30 synthetic events for AVENTIX for testing purposes.'

    def handle(self, *args, **kwargs):
        Event.objects.all().delete()
        
        departments = [Event.Department.CS, Event.Department.ENGINEERING, Event.Department.BUSINESS, Event.Department.ARTS, Event.Department.SCIENCE]
        event_types = [Event.EventType.WORKSHOP, Event.EventType.SEMINAR, Event.EventType.CONFERENCE, Event.EventType.MEETING]
        years = [Event.AcademicYear.YEAR_2023_2024, Event.AcademicYear.YEAR_2024_2025]
        
        events = []
        base_date = date(2023, 9, 1)

        # 1. Zero-registration
        events.append(Event(
            name="Ghost Seminar", event_type=Event.EventType.SEMINAR, department=Event.Department.CS,
            academic_year=Event.AcademicYear.YEAR_2023_2024, event_date=base_date, status=Event.Status.COMPLETED,
            registrations=0, attendance=0, completion=0, feedback_rating=None, feedback_responses=0
        ))

        # 2. Zero-attendance
        events.append(Event(
            name="No Show Workshop", event_type=Event.EventType.WORKSHOP, department=Event.Department.ENGINEERING,
            academic_year=Event.AcademicYear.YEAR_2023_2024, event_date=base_date + timedelta(days=1), status=Event.Status.COMPLETED,
            registrations=20, attendance=0, completion=0, feedback_rating=None, feedback_responses=0
        ))

        # 3. Zero-feedback-response
        events.append(Event(
            name="Silent Conference", event_type=Event.EventType.CONFERENCE, department=Event.Department.BUSINESS,
            academic_year=Event.AcademicYear.YEAR_2023_2024, event_date=base_date + timedelta(days=2), status=Event.Status.COMPLETED,
            registrations=50, attendance=45, completion=45, feedback_rating=None, feedback_responses=0
        ))

        # 4. 1-4 feedback responses
        events.append(Event(
            name="Low Feedback Meeting", event_type=Event.EventType.MEETING, department=Event.Department.ARTS,
            academic_year=Event.AcademicYear.YEAR_2023_2024, event_date=base_date + timedelta(days=3), status=Event.Status.COMPLETED,
            registrations=30, attendance=25, completion=25, feedback_rating=4.5, feedback_responses=2
        ))

        # 5. Attendance == registrations
        events.append(Event(
            name="Perfect Attendance Seminar", event_type=Event.EventType.SEMINAR, department=Event.Department.SCIENCE,
            academic_year=Event.AcademicYear.YEAR_2024_2025, event_date=base_date + timedelta(days=4), status=Event.Status.COMPLETED,
            registrations=40, attendance=40, completion=35, feedback_rating=4.8, feedback_responses=25
        ))

        # 6. Cancelled event
        events.append(Event(
            name="Cancelled Workshop", event_type=Event.EventType.WORKSHOP, department=Event.Department.CS,
            academic_year=Event.AcademicYear.YEAR_2024_2025, event_date=base_date + timedelta(days=5), status=Event.Status.CANCELLED,
            registrations=10, attendance=0, completion=0, feedback_rating=None, feedback_responses=0
        ))

        # 7. Deliberately Invalid Event (attendance > registrations) for Data Quality Warnings testing
        events.append(Event(
            name="Invalid Data Event", event_type=Event.EventType.WORKSHOP, department=Event.Department.CS,
            academic_year=Event.AcademicYear.YEAR_2024_2025, event_date=base_date + timedelta(days=6), status=Event.Status.COMPLETED,
            registrations=20, attendance=50, completion=10, feedback_rating=4.0, feedback_responses=10
        ))

        # Random Seed for reproducibility
        random.seed(42)

        # Normal events to make it exactly 30
        for i in range(7, 31):
            reg = random.randint(20, 200)
            att = random.randint(int(reg * 0.4), reg)
            comp = random.randint(int(att * 0.5), att)
            fb_resp = random.randint(5, att)
            fb_rat = round(random.uniform(2.5, 5.0), 1) if fb_resp > 0 else None
            
            # Ensure unique names
            events.append(Event(
                name=f"Standard Event {i}",
                event_type=random.choice(event_types),
                department=random.choice(departments),
                academic_year=random.choice(years),
                event_date=base_date + timedelta(days=i),
                status=Event.Status.COMPLETED,
                registrations=reg,
                attendance=att,
                completion=comp,
                feedback_rating=fb_rat,
                feedback_responses=fb_resp
            ))

        for event in events:
            try:
                event.clean()
            except Exception:
                pass # deliberately ignore so we can save invalid records
            event.save()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully generated 30 synthetic events.'))
