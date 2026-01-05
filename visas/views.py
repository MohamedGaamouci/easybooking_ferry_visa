from .models import VisaApplication, VisaForm
from .forms import (
    VisaApplicationForm,
    VisaApplicationAnswerForm,
    VisaApplicationDocumentForm, UpdateVisaStatusForm, VisaDestinationForm, VisaRequiredDocumentForm, VisaFormFieldForm
)
from django.views.decorators.http import require_POST
from django.shortcuts import reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.shortcuts import render
from .models import VisaApplication, VisaDestination

from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q

from django.contrib import messages

import json
# ========================================================
# 1. READ ALL (List View with Pagination & Stats)
# ========================================================
# @login_required
# @permission_required('visas.view_visaapplication', raise_exception=True)


def visa_list_view(request):
    """
    Renders the Visa Processing Center main page.
    Includes:
    - Status Statistics (New, Appointment, Embassy, Completed)
    - Paginated Table of Applications
    - Dropdowns for Filters
    """

    # --- A. STATISTICS (Efficient Counting) ---
    # We filter by the specific keys defined in your STATUS_CHOICES
    stats = {
        'new': VisaApplication.objects.filter(status='new').count(),
        'under_review': VisaApplication.objects.filter(status='review').count(),
        'appt': VisaApplication.objects.filter(status='appointment').count(),
        'embassy': VisaApplication.objects.filter(status='embassy').count(),
        'completed': VisaApplication.objects.filter(status='completed').count(),
        'rejected': VisaApplication.objects.filter(status='rejected').count(),
        'cancelled': VisaApplication.objects.filter(status='cancelled').count(),
        'ready': VisaApplication.objects.filter(status='ready').count(),
    }
    print(stats)

    # --- B. MAIN QUERY ---
    # Optimized: select_related fetches Agency & Destination in the same SQL query
    queryset = VisaApplication.objects.select_related(
        'agency',
        'destination'
    ).order_by('-created_at')

    # Optional: Filter by Destination if selected in dropdown
    dest_filter = request.GET.get('destination_id')
    if dest_filter and dest_filter.isdigit():
        queryset = queryset.filter(destination_id=int(dest_filter))

    # --- C. PAGINATION ---
    # Show 20 applications per page
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page', 1)

    try:
        applications = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        applications = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        applications = paginator.page(paginator.num_pages)

    # --- D. DROPDOWN DATA ---
    # For the manual add modal and filter dropdowns
    # destinations = VisaDestination.objects.filter(is_active=True)
    # agencies = Agency.objects.filter(status='active')

    context = {
        'applications': applications,  # The paginated object
        'stats': stats,               # The counters
        # 'destinations': destinations,  # For filters/modal
        # 'agencies': agencies,         # For modal
    }

    return render(request, 'admin/visa_application.html', context)


# ========================================================
# 2. READ ONE (API View for Modal)
# ========================================================


@login_required
@require_GET
def get_visa_details(request, app_id):
    """
    API: Fetches heavy details (Documents & Answers) for a single application.
    Called via AJAX when opening the Process Modal.
    """

    # 1. Fetch Application with Optimized Query
    # select_related fetches the parent Agency and Destination data instantly
    app = get_object_or_404(
        VisaApplication.objects.select_related('agency', 'destination'),
        id=app_id
    )

    # 2. Serialize Dynamic Form Answers
    answers_data = []
    # We order by 'field__order_index' so the form looks logical to the human eye
    for ans in app.answers.select_related('field').all().order_by('field__order_index'):
        answers_data.append({
            'label': ans.field.label,
            'value': ans.value
        })

    # 3. Serialize Uploaded Documents
    docs_data = []
    for doc in app.uploaded_documents.select_related('required_doc').all():
        # Safety: Check if file exists to prevent 500 Error on missing files
        file_url = doc.file.url if doc.file else None

        docs_data.append({
            'id': doc.id,
            'name': doc.required_doc.name,
            'url': file_url,
            'status': doc.status
        })

    # 4. Format Date for HTML Input
    # HTML5 datetime-local input requires format: "YYYY-MM-DDTHH:MM"
    appt_str = ""
    if app.embassy_appointment_date:
        appt_str = app.embassy_appointment_date.strftime('%Y-%m-%dT%H:%M')

    # 5. Construct Response
    data = {
        'id': app.id,
        'reference': app.reference,
        'applicant': f"{app.first_name} {app.last_name}",
        'agency_name': app.agency.company_name if app.agency else 'Direct Client',
        'destination': f"{app.destination.country} - {app.destination.visa_type}",
        'status': app.status,
        'admin_notes': app.admin_notes,
        'appointment_date': appt_str,
        'answers': answers_data,
        'documents': docs_data,
    }

    return JsonResponse(data)
# ========================================================
# 3. UPDATE API (Secure Transactional Update)
# ========================================================


@login_required
@require_POST
def update_visa_application(request):
    """
    API: Handles the 'Save Changes' action from the Process Modal.
    - Validates data using UpdateVisaStatusForm.
    - Uses Atomic Transaction to ensure data integrity.
    """
    try:
        # 1. Get the instance
        app_id = request.POST.get('application_id')
        app = get_object_or_404(VisaApplication, id=app_id)

        # 2. Bind data to the Form
        form = UpdateVisaStatusForm(request.POST, instance=app)

        # 3. Validation Step
        if form.is_valid():

            # 4. Transactional Save
            # 'update all or fail all' logic starts here
            with transaction.atomic():
                # Save the Application (Status, Notes, Date)
                updated_app = form.save()

                # Future-Proofing:
                # If you add logic here later (e.g., "Create Invoice" or "Send Email"),
                # and that logic fails, the status change above will ROLLBACK automatically.

                # Example:
                # if updated_app.status == 'completed':
                #     send_completion_email(updated_app)

            return JsonResponse({
                'status': 'success',
                'message': 'Application updated successfully'
            })

        else:
            # Validation Failed (e.g., Invalid Date format, missing fields)
            return JsonResponse({
                'status': 'error',
                'message': 'Validation Failed',
                'errors': form.errors.as_json()
            }, status=400)

    except Exception as e:
        # Unexpected System Error
        return JsonResponse({
            'status': 'error',
            'message': f"Server Error: {str(e)}"
        }, status=500)


# ========================================================
# 4. SCHEMA API (Get Form Fields for a Destination)
# ========================================================
@login_required
@require_GET
def get_visa_schema(request, destination_id):
    """
    API: Returns the Latest Form Structure for a destination.
    Used purely to RENDER the modal inputs (No DB writes).
    """
    destination = get_object_or_404(VisaDestination, id=destination_id)

    # 1. Fetch Latest Active Form
    latest_form = destination.forms.filter(
        is_active=True).order_by('-version').first()

    fields_data = []
    form_version_display = "No Form Assigned"

    if latest_form:
        form_version_display = f"v{latest_form.version}"
        # Get fields ordered by 'order_index'
        for field in latest_form.fields.all().order_by('order_index'):
            fields_data.append({
                'id': field.id,
                'label': field.label,
                'type': field.field_type,  # text, date, select, checkbox
                'options': field.options.split(',') if field.options else [],
                'required': field.is_required,
                'order': field.order_index
            })

    # 2. Fetch Required Documents
    docs_data = []
    for doc in destination.required_documents.filter(is_required=True):
        docs_data.append({
            'id': doc.id,
            'name': doc.name,
            'description': doc.description
        })

    return JsonResponse({
        'destination': destination.country,
        'visa_type': destination.visa_type,
        'form_version': form_version_display,  # <--- Added as requested
        'fields': fields_data,
        'documents': docs_data
    })


# ========================================================
# 5. DESTINATIONS LIST API (Lazy Load for Modal)
# ========================================================
@login_required
@require_GET
def get_visa_destinations_api(request):
    """
    API: Returns a list of all active Visa Destinations.
    Called via AJAX when the user clicks 'Add Manual App'.
    """
    destinations = VisaDestination.objects.filter(is_active=True).values(
        'id', 'country', 'visa_type', 'net_price', 'selling_price', 'processing_time'
    )

    # Convert QuerySet to List to make it JSON serializable
    data = list(destinations)

    return JsonResponse({'destinations': data})


@login_required
@require_POST
def visa_create_view(request):
    try:
        # 1. Parse JSON Data
        json_str = request.POST.get('json_data')
        if not json_str:
            return JsonResponse({'status': 'error', 'message': 'No data received'}, status=400)

        data = json.loads(json_str)
        main_info = data.get('main_info', {})
        answers_list = data.get('answers', [])

        # Start Transaction (All or Nothing)
        with transaction.atomic():

            # ====================================================
            # STEP A: Validate & Create Main Application
            # ====================================================
            # Map JSON keys to Form keys
            app_data = {
                'first_name': main_info.get('first_name'),
                'last_name': main_info.get('last_name'),
                'passport_number': main_info.get('passport_number'),
                # ID (Form handles ModelChoiceField IDs)
                'destination': main_info.get('destination'),
                'agency': main_info.get('agency_id'),       # ID
                'status': 'new'
            }

            app_form = VisaApplicationForm(data=app_data)

            if not app_form.is_valid():
                # Extract the first error message to show the user
                first_error = next(iter(app_form.errors.values()))[0]
                raise ValueError(f"Application Error: {first_error}")

            # Save parent to get the ID (needed for answers/docs)
            application = app_form.save()

            # ====================================================
            # STEP B: Validate & Create Answers
            # ====================================================
            for item in answers_list:
                ans_data = {
                    'application': application.id,
                    'field': int(item['field_id']),
                    'value': item['value']
                }

                # Check validation (clean_value logic)
                ans_form = VisaApplicationAnswerForm(data=ans_data)
                if not ans_form.is_valid():
                    raise ValueError(
                        f"Answer Error (Field {item['field_id']}): {ans_form.errors.as_text()}")

                ans_form.save()

            # ====================================================
            # STEP C: Validate & Create Documents
            # ====================================================
            for key, file_obj in request.FILES.items():
                if key.startswith('doc_'):
                    req_doc_id = int(key.split('_')[1])

                    doc_data = {
                        'application': application.id,
                        'required_doc': req_doc_id,
                        'status': 'pending'
                    }

                    # Pass 'data' for fields and 'files' for the file
                    doc_form = VisaApplicationDocumentForm(
                        data=doc_data, files={'file': file_obj})

                    if not doc_form.is_valid():
                        # This triggers your clean_file (size/extension check)
                        error_msg = doc_form.errors.get(
                            'file', ['Invalid file'])[0]
                        doc_name = file_obj.name
                        raise ValueError(
                            f"Document Error ({doc_name}): {error_msg}")

                    doc_form.save()

        # Success Response
        messages.success(
            request, f"Application #{application.reference} created successfully.")
        return JsonResponse({
            'status': 'success',
            'redirect_url': reverse('admin_visa_app')
        })

    except ValueError as ve:
        # Validation Errors (User fault)
        return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
    except Exception as e:
        # System Errors (Server fault)
        print(f"System Error: {e}")
        return JsonResponse({'status': 'error', 'message': "System Error occurred."}, status=500)


# ================================================================================================================
# 6. CREATE THE DESTINATION WITH IT'S DOCS AND FORM
# ================================================================================================================

@login_required
@permission_required('visas.add_visadestination', raise_exception=True)
@require_POST
def visa_destination_create_view(request):
    try:
        # 1. Parse JSON Payload
        json_str = request.POST.get('json_data')
        if not json_str:
            return JsonResponse({'status': 'error', 'message': 'No data received'}, status=400)

        data = json.loads(json_str)

        # Extract the 3 parts
        dest_data = data.get('visa_destination', {})
        docs_list = data.get('required_docs', [])
        fields_list = data.get('visa_form_fields', [])

        # Start Atomic Transaction (All or Nothing)
        with transaction.atomic():

            # ====================================================
            # STEP 1: CREATE DESTINATION
            # ====================================================
            # We pass request.FILES to handle the 'cover_image'
            dest_form = VisaDestinationForm(
                data=dest_data, files=request.FILES)

            if not dest_form.is_valid():
                # Get the first error message
                first_error = next(iter(dest_form.errors.values()))[0]
                raise ValueError(f"Destination Error: {first_error}")

            destination = dest_form.save()

            # ====================================================
            # STEP 2: CREATE REQUIRED DOCUMENTS
            # ====================================================
            for doc_item in docs_list:
                # Add the foreign key ID manually
                doc_item['destination'] = destination.id

                doc_form = VisaRequiredDocumentForm(data=doc_item)
                if not doc_form.is_valid():
                    raise ValueError(
                        f"Document Error ({doc_item.get('name')}): {doc_form.errors.as_text()}")

                doc_form.save()

            # ====================================================
            # STEP 3: CREATE VISA FORM & QUESTIONS
            # ====================================================
            # A. Create the parent Form Container (Version 1)
            # We create this manually since it doesn't need validation from the frontend
            visa_form = VisaForm.objects.create(
                destination=destination,
                version=1,
                is_active=True
            )

            # B. Create Fields attached to this Form
            for field_item in fields_list:
                # Add Foreign Key
                field_item['form'] = visa_form.id

                field_form = VisaFormFieldForm(data=field_item)
                if not field_form.is_valid():
                    raise ValueError(
                        f"Question Error ({field_item.get('label')}): {field_form.errors.as_text()}")

                field_form.save()

        # Success
        messages.success(
            request, f"Visa Destination '{destination.country}' created successfully.")
        return JsonResponse({'status': 'success'})

    except ValueError as ve:
        # Validation Errors (User input issues)
        return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)

    except Exception as e:
        # System Errors
        print(f"CRITICAL ERROR: {str(e)}")
        return JsonResponse({'status': 'error', 'message': "System Error. Check logs."}, status=500)


# ================================================================================================================
# 6. GET VISA DESTINAITON WITH THE ID AND IT'S NESTED TABLES
# ================================================================================================================

@login_required
@permission_required('visas.change_visadestination', raise_exception=True)
@require_POST
def visa_destination_update_view(request, pk):
    """
    METHOD: POST
    ACTION: Save the edited data.
    """
    try:
        dest = get_object_or_404(VisaDestination, pk=pk)

        # 1. Parse Data
        json_str = request.POST.get('json_data')
        if not json_str:
            return JsonResponse({'status': 'error', 'message': 'No data received'}, status=400)

        data = json.loads(json_str)
        dest_data = data.get('visa_destination', {})
        docs_list = data.get('required_docs', [])
        fields_list = data.get('visa_form_fields', [])
        print(dest_data)

        # 2. Save Everything Safely
        with transaction.atomic():
            # A. Update Main Info
            form = VisaDestinationForm(
                instance=dest, data=dest_data, files=request.FILES)
            if not form.is_valid():
                raise ValueError(
                    f"Info Error: {next(iter(form.errors.values()))[0]}")
            form.save()

            # B. Update Documents (Wipe old -> Add new)
            dest.required_documents.all().delete()
            for item in docs_list:
                item['destination'] = dest.id
                d_form = VisaRequiredDocumentForm(data=item)
                if d_form.is_valid():
                    d_form.save()

            # C. Update Questions (Wipe old -> Add new)
            active_form = dest.forms.filter(is_active=True).first()
            if not active_form:
                active_form = VisaForm.objects.create(
                    destination=dest, version=1)

            active_form.fields.all().delete()
            for item in fields_list:
                item['form'] = active_form.id
                f_form = VisaFormFieldForm(data=item)
                if f_form.is_valid():
                    f_form.save()

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def visa_destination_detail_api(request, pk):
    """
    METHOD: GET
    ACTION: Fetch current data to populate the modal.
    """
    # 1. Get the Destination
    dest = get_object_or_404(VisaDestination, pk=pk)

    # 2. Get Related Documents
    documents = list(dest.required_documents.values(
        'id', 'name', 'description', 'is_required'))

    # 3. Get Related Questions (from the active form)
    questions = []
    active_form = dest.forms.filter(
        is_active=True).order_by('-version').first()
    if active_form:
        questions = list(active_form.fields.values(
            'id', 'label', 'field_type', 'options', 'is_required', 'order_index'
        ))

    # 4. Return as JSON
    data = {
        'status': 'success',
        'destination': {
            'id': dest.id,
            'country': dest.country,
            'visa_name': dest.visa_name,
            'visa_type': dest.visa_type,
            'net_price': str(dest.net_price),
            'selling_price': str(dest.selling_price),
            'processing_time': dest.processing_time,
            'conditions': dest.conditions,
            'is_active': dest.is_active,
        },
        'documents': documents,
        'questions': questions
    }
    return JsonResponse(data)

# ========================================================
# CLIENT SIDE - PAGES
# ========================================================


@login_required
def get_client_visa_destinations_api(request):
    """
    AJAX API: Returns paginated list of destinations for the Grid.
    Filters by search query.
    """
    queryset = VisaDestination.objects.filter(
        is_active=True).order_by('country')

    # Search Filter
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(country__icontains=search) |
            Q(visa_name__icontains=search) |
            Q(visa_type__icontains=search)
        )

    # Pagination (8 cards per page)
    paginator = Paginator(queryset, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    data = []
    for dest in page_obj:
        data.append({
            'id': dest.id,
            'country': dest.country,
            'visa_name': dest.visa_name,
            'visa_type': dest.visa_type,
            'processing_time': dest.processing_time,
            'price': float(dest.selling_price),
            'cover_image': dest.cover_image.url if dest.cover_image else None,
        })

    return JsonResponse({
        'status': 'success',
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@login_required
def get_client_visa_detail_api(request, pk):
    """
    AJAX API: Returns FULL details for the Drawer (Conditions, Price, Docs).
    """
    dest = get_object_or_404(VisaDestination, pk=pk, is_active=True)

    # Get Required Documents Names for the list
    docs = list(dest.required_documents.all().values('name', 'description'))

    data = {
        'status': 'success',
        'id': dest.id,
        'country': dest.country,
        'visa_type': dest.visa_type,
        'visa_name': dest.visa_name,
        'processing_time': dest.processing_time,
        'price': float(dest.selling_price),
        'conditions': dest.conditions,  # <--- The text field you wanted
        'cover_image': dest.cover_image.url if dest.cover_image else None,
        'documents': docs
    }
    return JsonResponse(data)


@login_required
def visa_view(request):
    """Render the empty HTML shell. JS will load the data."""
    return render(request, 'client/visa_marketplace.html')


@login_required
def new_visa_view(request):
    """
    Client Application Page.
    The HTML/JS will read the '?destination_id=X' from the URL 
    and fetch the schema via API to build the form.
    """
    return render(request, 'client/visa_new_app.html')


def requests(request):
    return render(request, 'client/visa.html')
