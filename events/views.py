from django.shortcuts import render
from .analytics import compute_dashboard

def dashboard_view(request):
    context = compute_dashboard()
    return render(request, 'dashboard.html', context)
