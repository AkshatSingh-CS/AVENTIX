from django.db import models
from django.core.exceptions import ValidationError

class Event(models.Model):
    class EventType(models.TextChoices):
        WORKSHOP = 'Workshop', 'Workshop'
        SEMINAR = 'Seminar', 'Seminar'
        CONFERENCE = 'Conference', 'Conference'
        MEETING = 'Meeting', 'Meeting'

    class Department(models.TextChoices):
        CS = 'CS', 'Computer Science'
        ENGINEERING = 'Engineering', 'Engineering'
        BUSINESS = 'Business', 'Business'
        ARTS = 'Arts', 'Arts'
        SCIENCE = 'Science', 'Science'

    class AcademicYear(models.TextChoices):
        YEAR_2023_2024 = '2023-2024', '2023-2024'
        YEAR_2024_2025 = '2024-2025', '2024-2025'

    class Status(models.TextChoices):
        PLANNED = 'Planned', 'Planned'
        COMPLETED = 'Completed', 'Completed'
        CANCELLED = 'Cancelled', 'Cancelled'

    name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    department = models.CharField(max_length=50, choices=Department.choices)
    academic_year = models.CharField(max_length=20, choices=AcademicYear.choices)
    event_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices)
    registrations = models.PositiveIntegerField(default=0)
    attendance = models.PositiveIntegerField(default=0)
    completion = models.PositiveIntegerField(null=True, blank=True)
    feedback_rating = models.FloatField(null=True, blank=True)
    feedback_responses = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('name', 'event_date', 'department')

    def clean(self):
        super().clean()
        if self.registrations is not None and self.attendance is not None:
            if self.attendance > self.registrations:
                raise ValidationError({'attendance': 'Attendance cannot be greater than registrations.'})
        
        if self.attendance is not None and self.completion is not None:
            if self.completion > self.attendance:
                raise ValidationError({'completion': 'Completion cannot be greater than attendance.'})
        
        if self.feedback_rating is not None:
            if not (1.0 <= self.feedback_rating <= 5.0):
                raise ValidationError({'feedback_rating': 'Feedback rating must be between 1.0 and 5.0.'})
        
        # Note: PositiveIntegerField already enforces >= 0, but added here as requested as a second defense line
        if self.registrations is not None and self.registrations < 0:
            raise ValidationError({'registrations': 'Registrations must be >= 0.'})
        if self.attendance is not None and self.attendance < 0:
            raise ValidationError({'attendance': 'Attendance must be >= 0.'})
        if self.completion is not None and self.completion < 0:
            raise ValidationError({'completion': 'Completion must be >= 0.'})
        if self.feedback_responses is not None and self.feedback_responses < 0:
            raise ValidationError({'feedback_responses': 'Feedback responses must be >= 0.'})

    def __str__(self):
        return f"{self.name} ({self.event_date})"
