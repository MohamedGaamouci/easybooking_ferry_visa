from django.forms import ValidationError
from django.urls import reverse
from agencies.models import Agency
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
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q

from django.contrib import messages
from finance.services.invoice import create_single_service_invoice

import json
# ========================================================
# 1. READ ALL (List View with Pagination & Stats)
# ========================================================
# @login_required
# @permission_required('visas.view_visaapplication', raise_exception=True)


@login_required
def visa_list_view(request):
    """
     Renders the HTML Container for the Visa Dashboard.
     The actual data table is loaded via AJAX (JavaScript).
     """

    return render(request, 'admin/visa_application.html')


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
        VisaApplication.objects.select_related(
            'agency', 'destination'),
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
        'apply_by': app.apply_by.get_full_name() if app.apply_by else "Unknown",
        'user_admin': app.user_admin.get_full_name() if app.apply_by else "Unknown",
        'answers': answers_data,
        'documents': docs_data,
        'visa_document_url': app.visa_doc.url if app.visa_doc else None,
    }
    return JsonResponse(data)
# ========================================================
# 3. UPDATE API (Secure Transactional Update)
# ========================================================


@login_required
@require_POST
@login_required
@require_POST  # Good practice to restrict this to POST only
def update_visa_application(request):
    """
    API: Handles the 'Save Changes' action from the Process Modal.
    """
    try:
        app_id = request.POST.get('application_id')
        app = get_object_or_404(VisaApplication, id=app_id)

        # --- THE FIX IS HERE ---
        # You MUST pass request.FILES to the form, otherwise the file is ignored.
        form = UpdateVisaStatusForm(request.POST, request.FILES, instance=app)

        if form.is_valid():
            with transaction.atomic():
                updated_app = form.save()

                # Optional: specific logic if a file was uploaded
                if 'visa_doc' in request.FILES:
                    # e.g. Ensure status is set to ready if a doc is uploaded
                    if updated_app.status not in ['ready', 'completed']:
                        updated_app.status = 'ready'
                        updated_app.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Application updated successfully'
            })

        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Validation Failed',
                'errors': form.errors.as_json()
            }, status=400)

    except Exception as e:
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


# Import your Finance Models

# Import your Visa/App Models & Forms

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

        # Start Transaction
        with transaction.atomic():

            # --- STEP A: Main Application ---
            app_data = {
                'first_name': main_info.get('first_name'),
                'last_name': main_info.get('last_name'),
                'passport_number': main_info.get('passport_number'),
                'destination': main_info.get('destination'),
                'agency': main_info.get('agency_id'),
                'status': 'new'
            }

            app_form = VisaApplicationForm(data=app_data)
            if not app_form.is_valid():
                first_error = next(iter(app_form.errors.values()))[0]
                raise ValueError(f"Application Error: {first_error}")

            application = app_form.save()

            # --- STEP B: Answers ---
            for item in answers_list:
                ans_data = {
                    'application': application.id,
                    'field': int(item['field_id']),
                    'value': item['value']
                }
                ans_form = VisaApplicationAnswerForm(data=ans_data)
                if not ans_form.is_valid():
                    raise ValueError(
                        f"Answer Error: {ans_form.errors.as_text()}")
                ans_form.save()

            # --- STEP C: Documents ---
            for key, file_obj in request.FILES.items():
                if key.startswith('doc_'):
                    req_doc_id = int(key.split('_')[1])
                    doc_data = {
                        'application': application.id,
                        'required_doc': req_doc_id,
                        'status': 'pending'
                    }
                    doc_form = VisaApplicationDocumentForm(
                        data=doc_data, files={'file': file_obj})
                    if not doc_form.is_valid():
                        error_msg = doc_form.errors.get(
                            'file', ['Invalid file'])[0]
                        raise ValueError(f"Document Error: {error_msg}")
                    doc_form.save()

            # --- STEP D: FINANCE (The Bridge) ---

            # 1. Get Destination & Price
            destination = application.destination
            if not destination:
                raise ValueError("Destination not found.")

            price = destination.selling_price
            if not price or price <= 0:
                raise ValueError(
                    f"Selling price is not set for {destination.country}")

            # 2. CREATE INVOICE (Gate 1 Check happens here)
            # We call it 'generated_invoice' to avoid variable name conflicts
            generated_invoice = create_single_service_invoice(
                service_object=application,
                amount=price,
                description=f"Visa App: {application.first_name} {application.last_name} -> {destination.country}",
                user=request.user
            )

            # 3. Link Application to Invoice
            application.invoice = generated_invoice
            application.save()

        # Success Response (Outside Transaction)
        messages.success(
            request, f"Application #{application.reference} created. Invoice #{generated_invoice.invoice_number} generated.")

        return JsonResponse({
            'status': 'success',
            'redirect_url': reverse('admin_visa_app')
        })

    except ValidationError as ve:
        # This catches "Credit Limit Reached" errors
        msg = ve.message if hasattr(ve, 'message') else str(ve)
        return JsonResponse({'status': 'error', 'message': msg}, status=400)

    except ValueError as ve:
        # This catches Form/Logic errors
        return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)

    except Exception as e:
        # This catches unexpected crashes
        print(f"System Error: {e}")
        return JsonResponse({'status': 'error', 'message': f"System Error: {str(e)}"}, status=500)

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
# End Point for AJAX (Feltering)
# ========================================================

@login_required
def get_admin_visa_list_api(request):
    """
    AJAX API for Admin Visa Dashboard.
    Handles: Stats counting, Search, Filtering, Pagination.
    """
    # 1. Base Query
    # ADDED 'apply_by' to select_related to prevent N+1 queries
    qs = VisaApplication.objects.select_related(
        'agency', 'destination', 'apply_by'
    ).order_by('-created_at')

    # 2. Search (Ref, Name, Passport, Agency, Destination)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(reference__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(passport_number__icontains=search) |
            Q(agency__company_name__icontains=search) |
            Q(destination__country__icontains=search)
        )

    # 3. Calculate Stats (Live counts based on current search)
    stats = {
        'new': qs.filter(status='new').count(),
        'review': qs.filter(status='review').count(),
        'appt': qs.filter(status='appointment').count(),
        'embassy': qs.filter(status='embassy').count(),
        'ready': qs.filter(status='ready').count(),
        'completed': qs.filter(status='completed').count(),
        'rejected': qs.filter(status='rejected').count(),
        'cancelled': qs.filter(status='cancelled').count(),
    }

    # 4. Status Filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    # 5. Destination Filter
    dest_filter = request.GET.get('destination', '').strip()
    if dest_filter:
        qs = qs.filter(destination_id=dest_filter)

    # 6. Pagination
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 7. Serialize Data
    data = []
    for app in page_obj:
        # Agency Name Handling
        agency_name = app.agency.company_name if app.agency else "Direct Client"

        # Cover Image Handling
        cover_img = None
        if app.destination.cover_image:
            cover_img = app.destination.cover_image.url

        # --- ADDED: Apply By Logic ---
        applied_by_name = "System"
        if app.apply_by:
            full_name = app.apply_by.get_full_name()
            applied_by_name = full_name if full_name else app.apply_by.username

        data.append({
            'id': app.id,
            'reference': app.reference,
            'applicant': f"{app.first_name} {app.last_name}",
            'passport': app.passport_number,
            'agency': agency_name,
            'apply_by': applied_by_name,  # <--- Sent to frontend here
            'country': app.destination.country,
            'visa_type': app.destination.visa_type,
            'cover_image': cover_img,
            'status': app.status,
            'status_label': app.get_status_display(),
            'created_at': app.created_at.strftime('%Y-%m-%d'),
        })

    return JsonResponse({
        'status': 'success',
        'stats': stats,
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@login_required
def search_agencies_api(request):
    """
    AJAX API to search for agencies by name.
    """
    query = request.GET.get('q', '').strip()

    # 1. Base query: select_related is not needed with .values(),
    # but we use the relationship 'account__balance'
    agencies = Agency.objects.filter(status='active')

    if query:
        agencies = agencies.filter(company_name__icontains=query)

    # 2. Extract values using the database relationship field name
    # We rename 'account__balance' to 'balance' in the dictionary for the frontend
    results_qs = agencies.values('id', 'company_name', 'account__balance')[:20]

    # 3. Format the results so the keys look clean for the JS
    results = []
    for ag in results_qs:
        results.append({
            'id': ag['id'],
            'company_name': ag['company_name'],
            'current_balance': float(ag['account__balance'] or 0.00)
        })

    return JsonResponse({
        'status': 'success',
        'agencies': results
    })


@login_required
def get_all_destinations_api(request):
    """
    API: Returns all active destinations for dropdown filters.
    Usage: /api/visas/destinations/all/
    """
    destinations = VisaDestination.objects.filter(is_active=True).values(
        'id', 'country', 'visa_type'
    ).order_by('country')

    return JsonResponse({
        'status': 'success',
        'destinations': list(destinations)
    })
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


# Requets client side

# visas/views.py

@login_required
@require_GET
def get_client_applications_api(request):
    """
    AJAX API: Returns filtered list of Visa Applications for the current Agency/User.
    """
    # 1. Base Query: Filter by User's Agency
    user_agency = getattr(request.user, 'agency', None)
    if not user_agency:
        return JsonResponse({'status': 'error', 'message': 'No agency assigned.'}, status=403)

    qs = VisaApplication.objects.filter(agency=user_agency).select_related(
        'destination').order_by('-created_at')

    # 2. Search (Applicant Name, Ref, Destination, Passport)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(reference__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(passport_number__icontains=search) |
            Q(destination__country__icontains=search)
        )

    # 3. Filters
    status = request.GET.get('status')
    if status and status != 'all':
        qs = qs.filter(status=status)

    date = request.GET.get('date')  # Submitted Date
    if date:
        qs = qs.filter(created_at__date=date)

    # 4. Stats Calculation (Live for this filtered set or overall?)
    # Usually stats are for "Overall" state, so we run a separate quick aggregate on the base set
    base_qs = VisaApplication.objects.filter(agency=user_agency)
    stats = {
        'processing': base_qs.filter(status__in=['new', 'review', 'embassy']).count(),
        'appointment': base_qs.filter(status='appointment').count(),
        'ready': base_qs.filter(status='ready').count(),
        'action': base_qs.filter(status__in=['rejected', 'missing_docs']).count()
    }

    # 5. Pagination
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 6. Serialize Data
    data = []
    for app in page_obj:
        data.append({
            'id': app.id,
            'reference': app.reference,
            'applicant': f"{app.first_name} {app.last_name}",
            'passport': app.passport_number,
            'destination': app.destination.country,
            'destination_flag': "🏳️",  # You could add a flag field to your model later
            'submitted_on': app.created_at.strftime('%b %d, %Y'),
            'status': app.status,
            'status_label': app.get_status_display(),  # Uses choices display
        })

    return JsonResponse({
        'status': 'success',
        'stats': stats,
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })

# Client Page View (Render Empty HTML)


@login_required
def requests(request):
    return render(request, 'client/visa.html')
