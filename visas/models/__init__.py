# visas/
# ├── models/
# │   ├── __init__.py
# │   │
# │   ├── # 1. The Configuration (Admin Side)
# │   ├── visa_destination.py       <-- "France", "Turkey"
# │   ├── visa_form.py              <-- Container for the questions
# │   ├── visa_form_field.py        <-- "Passport Number", "Birth Date"
# │   ├── visa_required_document.py <-- "Passport Scan", "Bank Statement"
# │   │
# │   ├── # 2. The Application (Client Side)
# │   ├── visa_application.py          <-- The main record
# │   ├── visa_application_answer.py   <-- Answers to the questions
# │   └── visa_application_document.py <-- The uploaded files

from .visa_destination import VisaDestination
from .visa_form import VisaForm
from .visa_form_field import VisaFormField
from .visa_required_document import VisaRequiredDocument
from .visa_application import VisaApplication
from .visa_application_answer import VisaApplicationAnswer
from .visa_application_document import VisaApplicationDocument
