from django.http import JsonResponse
from .models import VisaApplication
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import VisaApplication, VisaDestination
from agencies.models import Agency


def admin_visa_app_view(request):
    """
    Renders the Visa Processing Center (Kanban & Table).
    """

    # 1. HANDLE MANUAL APPLICATION SUBMISSION (POST)
    if request.method == 'POST':
        # Extract data from the manual modal form
        agency_id = request.POST.get('agency')
        dest_id = request.POST.get('destination')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        passport = request.POST.get('passport_number')

        try:
            # Create the application
            new_app = VisaApplication.objects.create(
                # Handle "Direct Walk-in" (None)
                agency_id=agency_id if agency_id else None,
                destination_id=dest_id,
                first_name=first_name,
                last_name=last_name,
                passport_number=passport,
                status='new'  # Default status
            )
            messages.success(
                request, f"Application #{new_app.reference} created successfully.")
            return redirect('admin_visa_app')

        except Exception as e:
            messages.error(request, f"Error creating application: {str(e)}")

    # 2. FETCH DATA FOR THE UI (GET)

    # A. Stats Counters
    count_new = VisaApplication.objects.filter(status='new').count()
    count_appt = VisaApplication.objects.filter(status='appointment').count()
    count_embassy = VisaApplication.objects.filter(status='embassy').count()
    count_completed = VisaApplication.objects.filter(
        status='completed').count()

    # B. Dropdown Data (for Filters & Modals)
    destinations = VisaDestination.objects.filter(is_active=True)
    agencies = Agency.objects.filter(status='active')

    # C. Main Table Data
    # Use select_related to fetch linked Agency and Destination data in 1 query (Fast)
    applications = VisaApplication.objects.select_related(
        'agency',
        'destination'
    ).all().order_by('-created_at')

    context = {
        'applications': applications,
        'destinations': destinations,
        'agencies': agencies,
        'count_new': count_new,
        'count_appt': count_appt,
        'count_embassy': count_embassy,
        'count_completed': count_completed,
    }

    return render(request, 'admin/visa_application.html', context)


def get_visa_details(request, app_id):
    """
    API: Fetches heavy details (Documents & Answers) for a single application.
    Called via AJAX when opening the modal.
    """
    app = get_object_or_404(VisaApplication, id=app_id)

    # 1. Fetch Dynamic Form Answers
    answers_data = []
    for ans in app.answers.select_related('field').all():
        answers_data.append({
            'label': ans.field.label,
            'value': ans.value
        })

    # 2. Fetch Uploaded Documents
    docs_data = []
    for doc in app.uploaded_documents.select_related('required_doc').all():
        docs_data.append({
            'id': doc.id,
            'name': doc.required_doc.name,
            'url': doc.file.url,
            'status': doc.status
        })

    data = {
        'id': app.id,
        'reference': app.reference,
        'applicant': f"{app.first_name} {app.last_name}",
        'status': app.status,
        'admin_notes': app.admin_notes,
        'appointment_date': app.embassy_appointment_date.strftime('%Y-%m-%dT%H:%M') if app.embassy_appointment_date else '',
        'answers': answers_data,
        'documents': docs_data,
    }

    return JsonResponse(data)
