# from django.db import transaction
# from .models import (
#     VisaApplication,
#     VisaApplicationAnswer,
#     VisaApplicationDocument,
#     VisaFormField,
#     VisaRequiredDocument
# )


# def create_visa_application_service(form, request_post, request_files):
#     """
#     Transactional Service to create a complete Visa Application.
#     1. Saves the Main Application (from the validated form).
#     2. Extracts & Saves Dynamic Answers (field_{id}).
#     3. Extracts & Saves Dynamic Documents (doc_{id}).
#     """
#     with transaction.atomic():
#         # 1. SAVE PARENT APPLICATION
#         # The form is already validated in the view, we just save it.
#         application = form.save(commit=False)
#         application.status = 'new'  # Ensure status is New
#         application.save()

#         destination = application.destination

#         # 2. PROCESS DYNAMIC FORM ANSWERS
#         # Find the active form for this destination
#         active_form = destination.forms.filter(
#             is_active=True).order_by('-version').first()

#         if active_form:
#             answers_to_create = []
#             # Loop through the questions defined in the DB
#             for field_obj in active_form.fields.all():
#                 # Construct the key we expect from frontend, e.g., "field_25"
#                 input_key = f"field_{field_obj.id}"

#                 # Get the value from POST data, default to empty string
#                 user_answer = request_post.get(input_key, "").strip()

#                 # Create the answer object
#                 answers_to_create.append(VisaApplicationAnswer(
#                     application=application,
#                     field=field_obj,
#                     value=user_answer
#                 ))

#             # Bulk save for performance
#             if answers_to_create:
#                 VisaApplicationAnswer.objects.bulk_create(answers_to_create)

#         # 3. PROCESS DYNAMIC DOCUMENTS
#         # Loop through requirements defined in the DB
#         docs_to_create = []
#         required_docs = destination.required_documents.filter(is_required=True)

#         for req_doc in required_docs:
#             input_key = f"doc_{req_doc.id}"

#             # Check if file was uploaded
#             if input_key in request_files:
#                 uploaded_file = request_files[input_key]
#                 docs_to_create.append(VisaApplicationDocument(
#                     application=application,
#                     required_doc=req_doc,
#                     file=uploaded_file,
#                     status='pending'
#                 ))
#             else:
#                 # Optional: Create a placeholder record saying "Missing" if needed,
#                 # or just skip. Here we skip to keep DB clean,
#                 # or you can create one with status='rejected' to flag it.
#                 pass

#         if docs_to_create:
#             VisaApplicationDocument.objects.bulk_create(docs_to_create)

#         return application
