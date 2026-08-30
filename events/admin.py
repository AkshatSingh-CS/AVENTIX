from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'department', 'event_date', 'status', 'registrations', 'attendance')
    list_filter = ('event_type', 'department', 'academic_year', 'status')
    search_fields = ('name',)
