"""
Indian KYC / Document Verification — Master Document Type Registry

Covers all commonly accepted documents as per:
- RBI KYC Master Directions
- SEBI KYC norms
- IRDAI regulations
- PMLA (Prevention of Money Laundering Act)
- Aadhaar Act
"""

from typing import TypedDict


class DocumentType(TypedDict):
    key: str
    name: str
    category: str
    description: str
    issuing_authority: str
    is_ovi: bool          # Officially Valid Identity document under PMLA
    is_opa: bool          # Officially Valid Address Proof
    common_fields: list[str]


DOCUMENT_TYPES: list[DocumentType] = [

    # ─── IDENTITY DOCUMENTS ───────────────────────────────────────────────────

    {
        "key": "aadhaar_card",
        "name": "Aadhaar Card",
        "category": "identity",
        "description": "12-digit unique identification number issued by UIDAI. Accepted as both identity and address proof.",
        "issuing_authority": "Unique Identification Authority of India (UIDAI)",
        "is_ovi": True,
        "is_opa": True,
        "common_fields": ["aadhaar_number", "name", "date_of_birth", "gender", "address", "photo"],
    },
    {
        "key": "pan_card",
        "name": "PAN Card",
        "category": "identity",
        "description": "Permanent Account Number issued by the Income Tax Department. Mandatory for financial transactions above ₹50,000.",
        "issuing_authority": "Income Tax Department, Government of India",
        "is_ovi": True,
        "is_opa": False,
        "common_fields": ["pan_number", "name", "father_name", "date_of_birth", "photo"],
    },
    {
        "key": "passport",
        "name": "Passport",
        "category": "identity",
        "description": "Indian Passport issued by Ministry of External Affairs. Serves as both identity and address proof.",
        "issuing_authority": "Ministry of External Affairs, Government of India",
        "is_ovi": True,
        "is_opa": True,
        "common_fields": ["passport_number", "name", "date_of_birth", "expiry_date", "address", "photo"],
    },
    {
        "key": "voter_id",
        "name": "Voter ID Card (EPIC)",
        "category": "identity",
        "description": "Electoral Photo Identity Card issued by the Election Commission of India.",
        "issuing_authority": "Election Commission of India",
        "is_ovi": True,
        "is_opa": True,
        "common_fields": ["epic_number", "name", "father_name", "address", "photo"],
    },
    {
        "key": "driving_license",
        "name": "Driving License",
        "category": "identity",
        "description": "Driving License issued by Regional Transport Authority (RTA). Valid as both identity and address proof.",
        "issuing_authority": "Regional Transport Authority (RTA)",
        "is_ovi": True,
        "is_opa": True,
        "common_fields": ["dl_number", "name", "date_of_birth", "address", "expiry_date", "vehicle_classes", "photo"],
    },
    {
        "key": "nrega_job_card",
        "name": "NREGA Job Card",
        "category": "identity",
        "description": "Job card issued under the Mahatma Gandhi National Rural Employment Guarantee Act.",
        "issuing_authority": "Ministry of Rural Development",
        "is_ovi": True,
        "is_opa": False,
        "common_fields": ["job_card_number", "name", "address"],
    },
    {
        "key": "digilocker_aadhaar",
        "name": "DigiLocker Aadhaar",
        "category": "identity",
        "description": "Digitally verified Aadhaar document from DigiLocker.",
        "issuing_authority": "UIDAI via DigiLocker (MeitY)",
        "is_ovi": True,
        "is_opa": True,
        "common_fields": ["aadhaar_number", "name", "date_of_birth", "gender", "address"],
    },

    # ─── ADDRESS PROOF ────────────────────────────────────────────────────────

    {
        "key": "electricity_bill",
        "name": "Electricity Bill",
        "category": "address",
        "description": "Latest electricity bill (not older than 3 months).",
        "issuing_authority": "State Electricity Board / Distribution Company",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["consumer_number", "name", "address", "bill_date", "bill_amount"],
    },
    {
        "key": "water_bill",
        "name": "Water / Municipal Bill",
        "category": "address",
        "description": "Latest water or municipal utility bill (not older than 3 months).",
        "issuing_authority": "Municipal Corporation / Local Body",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["consumer_number", "name", "address", "bill_date"],
    },
    {
        "key": "gas_connection_bill",
        "name": "Gas Connection Bill / Piped Gas Bill",
        "category": "address",
        "description": "Piped natural gas or cylinder gas connection bill.",
        "issuing_authority": "Gas Distribution Company (IGL, MGL, etc.)",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["consumer_number", "name", "address", "bill_date"],
    },
    {
        "key": "telephone_bill",
        "name": "Telephone / Broadband Bill",
        "category": "address",
        "description": "Latest landline telephone or broadband bill (not older than 3 months).",
        "issuing_authority": "Telecom Service Provider (BSNL, Airtel, etc.)",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["phone_number", "name", "address", "bill_date"],
    },
    {
        "key": "bank_statement_address",
        "name": "Bank Account Statement (Address Proof)",
        "category": "address",
        "description": "Bank account statement showing current address (not older than 3 months).",
        "issuing_authority": "Scheduled Commercial Bank",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["account_number", "name", "address", "statement_period"],
    },
    {
        "key": "rent_agreement",
        "name": "Rent / Lease Agreement",
        "category": "address",
        "description": "Registered rent or lease agreement with current address.",
        "issuing_authority": "Sub-Registrar Office",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["tenant_name", "landlord_name", "address", "start_date", "end_date"],
    },
    {
        "key": "property_tax_receipt",
        "name": "Property Tax Receipt",
        "category": "address",
        "description": "Latest municipal property tax receipt.",
        "issuing_authority": "Municipal Corporation / Gram Panchayat",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["owner_name", "property_address", "assessment_year"],
    },
    {
        "key": "ration_card",
        "name": "Ration Card",
        "category": "address",
        "description": "Ration card issued by State Food & Civil Supplies Department.",
        "issuing_authority": "State Government / Food & Civil Supplies Department",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["card_number", "head_of_family", "address", "members"],
    },

    # ─── INCOME / FINANCIAL ───────────────────────────────────────────────────

    {
        "key": "salary_slip",
        "name": "Salary Slip",
        "category": "income",
        "description": "Latest 3 months salary slip from employer.",
        "issuing_authority": "Employer / Company HR",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["employee_name", "employee_id", "designation", "basic_salary", "gross_salary", "net_salary", "month_year"],
    },
    {
        "key": "form_16",
        "name": "Form 16 (TDS Certificate)",
        "category": "income",
        "description": "Annual TDS certificate issued by employer. Confirms salary income and tax deducted.",
        "issuing_authority": "Employer (as per Income Tax Act)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["employee_name", "pan_number", "employer_name", "total_income", "tax_deducted", "financial_year"],
    },
    {
        "key": "itr_acknowledgement",
        "name": "Income Tax Return (ITR) Acknowledgement",
        "category": "income",
        "description": "ITR acknowledgement / Saral form for the last 2-3 financial years.",
        "issuing_authority": "Income Tax Department",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["pan_number", "name", "assessment_year", "total_income", "tax_paid", "acknowledgement_number"],
    },
    {
        "key": "bank_statement_6months",
        "name": "Bank Statement (6 Months)",
        "category": "income",
        "description": "Last 6 months bank account statement reflecting income and transactions.",
        "issuing_authority": "Scheduled Commercial Bank",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["account_number", "account_holder_name", "bank_name", "ifsc_code", "statement_period", "average_balance"],
    },
    {
        "key": "bank_statement_12months",
        "name": "Bank Statement (12 Months)",
        "category": "income",
        "description": "Last 12 months bank account statement for business/self-employed applicants.",
        "issuing_authority": "Scheduled Commercial Bank",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["account_number", "account_holder_name", "bank_name", "ifsc_code", "statement_period"],
    },
    {
        "key": "ca_certified_financials",
        "name": "CA Certified Financial Statements",
        "category": "income",
        "description": "Audited P&L, Balance Sheet certified by a Chartered Accountant (for self-employed).",
        "issuing_authority": "Chartered Accountant (ICAI member)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["business_name", "ca_name", "ca_registration_number", "financial_year", "net_profit", "turnover"],
    },
    {
        "key": "appointment_letter",
        "name": "Employment Appointment Letter",
        "category": "income",
        "description": "Latest appointment or offer letter from the current employer.",
        "issuing_authority": "Employer",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["employee_name", "designation", "joining_date", "ctc", "employer_name"],
    },

    # ─── BUSINESS DOCUMENTS ───────────────────────────────────────────────────

    {
        "key": "gst_certificate",
        "name": "GST Registration Certificate",
        "category": "business",
        "description": "GST registration certificate showing GSTIN.",
        "issuing_authority": "Goods and Services Tax Network (GSTN)",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["gstin", "business_name", "trade_name", "registration_date", "business_address"],
    },
    {
        "key": "certificate_of_incorporation",
        "name": "Certificate of Incorporation",
        "category": "business",
        "description": "Certificate issued by Registrar of Companies (ROC) for private/public limited companies.",
        "issuing_authority": "Registrar of Companies (MCA)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["cin_number", "company_name", "incorporation_date", "registered_address"],
    },
    {
        "key": "moa",
        "name": "Memorandum of Association (MOA)",
        "category": "business",
        "description": "Constitutional document of the company defining objectives.",
        "issuing_authority": "Registrar of Companies (MCA)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["company_name", "registered_address", "authorized_capital", "objectives"],
    },
    {
        "key": "aoa",
        "name": "Articles of Association (AOA)",
        "category": "business",
        "description": "Document defining the internal rules and regulations of the company.",
        "issuing_authority": "Registrar of Companies (MCA)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["company_name", "directors", "share_capital"],
    },
    {
        "key": "partnership_deed",
        "name": "Partnership Deed",
        "category": "business",
        "description": "Registered partnership deed for partnership firms.",
        "issuing_authority": "Sub-Registrar Office",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["firm_name", "partners", "profit_sharing_ratio", "business_address", "registration_date"],
    },
    {
        "key": "msme_registration",
        "name": "MSME / Udyam Registration Certificate",
        "category": "business",
        "description": "Udyam registration certificate for Micro, Small & Medium Enterprises.",
        "issuing_authority": "Ministry of MSME",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["udyam_registration_number", "enterprise_name", "type", "activity", "nic_code"],
    },
    {
        "key": "trade_license",
        "name": "Trade License",
        "category": "business",
        "description": "Trade license issued by local municipal body allowing business operations.",
        "issuing_authority": "Municipal Corporation / Local Body",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["license_number", "business_name", "business_address", "validity"],
    },
    {
        "key": "shop_establishment_certificate",
        "name": "Shop & Establishment Certificate",
        "category": "business",
        "description": "Certificate under the Shops and Establishments Act.",
        "issuing_authority": "State Labour Department",
        "is_ovi": False,
        "is_opa": True,
        "common_fields": ["registration_number", "establishment_name", "address", "validity"],
    },
    {
        "key": "board_resolution",
        "name": "Board Resolution",
        "category": "business",
        "description": "Board resolution authorizing the signatory for the transaction.",
        "issuing_authority": "Company Board",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["company_name", "resolution_date", "authorized_signatory"],
    },

    # ─── PROPERTY DOCUMENTS ───────────────────────────────────────────────────

    {
        "key": "sale_deed",
        "name": "Sale Deed / Agreement to Sale",
        "category": "property",
        "description": "Registered sale deed proving ownership of the property.",
        "issuing_authority": "Sub-Registrar Office",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["seller_name", "buyer_name", "property_address", "registration_date", "property_value"],
    },
    {
        "key": "encumbrance_certificate",
        "name": "Encumbrance Certificate (EC)",
        "category": "property",
        "description": "Certificate confirming the property is free from monetary and legal liabilities.",
        "issuing_authority": "Sub-Registrar Office",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["property_address", "survey_number", "period", "owner_name"],
    },
    {
        "key": "property_tax_document",
        "name": "Property Tax Paid Receipt",
        "category": "property",
        "description": "Latest property tax paid receipt from municipal corporation.",
        "issuing_authority": "Municipal Corporation",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["property_id", "owner_name", "property_address", "tax_year", "amount_paid"],
    },
    {
        "key": "title_search_report",
        "name": "Title Search Report",
        "category": "property",
        "description": "Legal report certifying clear title of the property for the last 30 years.",
        "issuing_authority": "Advocate / Title Search Company",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["property_address", "survey_number", "owner_chain", "encumbrances"],
    },
    {
        "key": "building_plan_approval",
        "name": "Building Plan Approval",
        "category": "property",
        "description": "Approved building plan from competent authority.",
        "issuing_authority": "Municipal Corporation / Development Authority",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["owner_name", "property_address", "approval_number", "approval_date"],
    },
    {
        "key": "noc_society",
        "name": "NOC from Housing Society",
        "category": "property",
        "description": "No Objection Certificate from the housing society.",
        "issuing_authority": "Registered Housing Society",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["society_name", "flat_number", "applicant_name", "date"],
    },
    {
        "key": "khata_certificate",
        "name": "Khata Certificate / Khata Extract",
        "category": "property",
        "description": "Khata certificate from BBMP or municipal authority showing property assessment.",
        "issuing_authority": "BBMP / Municipal Corporation",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["khata_number", "owner_name", "property_address", "area"],
    },

    # ─── VEHICLE DOCUMENTS ────────────────────────────────────────────────────

    {
        "key": "rc_book",
        "name": "Registration Certificate (RC Book)",
        "category": "vehicle",
        "description": "Vehicle registration certificate from RTO.",
        "issuing_authority": "Regional Transport Office (RTO)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["registration_number", "owner_name", "engine_number", "chassis_number", "make_model", "registration_date"],
    },
    {
        "key": "vehicle_insurance",
        "name": "Vehicle Insurance Certificate",
        "category": "vehicle",
        "description": "Valid vehicle insurance policy document.",
        "issuing_authority": "General Insurance Company",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["policy_number", "vehicle_number", "owner_name", "insurer_name", "validity"],
    },
    {
        "key": "puc_certificate",
        "name": "PUC Certificate",
        "category": "vehicle",
        "description": "Pollution Under Control (PUC) certificate for vehicle.",
        "issuing_authority": "Authorized PUC Testing Centre",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["vehicle_number", "test_date", "validity", "emission_values"],
    },

    # ─── MEDICAL / INSURANCE ─────────────────────────────────────────────────

    {
        "key": "medical_reports",
        "name": "Medical Reports / Health Records",
        "category": "medical",
        "description": "Medical examination reports, diagnostic test reports, or health records.",
        "issuing_authority": "Registered Hospital / Diagnostic Centre",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["patient_name", "doctor_name", "hospital_name", "report_date", "diagnosis"],
    },
    {
        "key": "hospital_bills",
        "name": "Hospital Bills / Medical Bills",
        "category": "medical",
        "description": "Original hospital or medical bills for insurance claim.",
        "issuing_authority": "Registered Hospital",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["patient_name", "hospital_name", "admission_date", "discharge_date", "total_amount"],
    },
    {
        "key": "discharge_summary",
        "name": "Discharge Summary",
        "category": "medical",
        "description": "Discharge summary from hospital after treatment.",
        "issuing_authority": "Registered Hospital",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["patient_name", "doctor_name", "diagnosis", "treatment", "discharge_date"],
    },
    {
        "key": "previous_insurance_policy",
        "name": "Previous Insurance Policy",
        "category": "medical",
        "description": "Copy of the existing or previous insurance policy.",
        "issuing_authority": "Insurance Company (IRDAI licensed)",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["policy_number", "insured_name", "sum_assured", "policy_start", "policy_end", "premium"],
    },
    {
        "key": "death_certificate",
        "name": "Death Certificate",
        "category": "medical",
        "description": "Death certificate issued by municipal authority (for life insurance claims).",
        "issuing_authority": "Municipal Corporation / Gram Panchayat",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["deceased_name", "date_of_death", "cause_of_death", "registration_number"],
    },
    {
        "key": "fir_copy",
        "name": "FIR Copy (Police Report)",
        "category": "medical",
        "description": "First Information Report for accident / theft claims.",
        "issuing_authority": "Police Station",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["fir_number", "police_station", "date_of_incident", "complainant_name"],
    },

    # ─── AGRICULTURE ──────────────────────────────────────────────────────────

    {
        "key": "kisan_credit_card",
        "name": "Kisan Credit Card",
        "category": "agriculture",
        "description": "Kisan Credit Card issued by bank to farmers for agricultural credit.",
        "issuing_authority": "Scheduled Commercial Bank / NABARD",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["card_number", "farmer_name", "bank_name", "credit_limit", "validity"],
    },
    {
        "key": "land_records_7_12",
        "name": "Land Records (7/12 Extract / RTC)",
        "category": "agriculture",
        "description": "Land record extract (7/12 Utara in Maharashtra, RTC in Karnataka) proving land ownership.",
        "issuing_authority": "Talathi / Tahsildar / State Revenue Department",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["survey_number", "owner_name", "village", "taluka", "district", "area", "crops"],
    },
    {
        "key": "crop_insurance_policy",
        "name": "Crop Insurance Policy (PMFBY)",
        "category": "agriculture",
        "description": "Pradhan Mantri Fasal Bima Yojana crop insurance policy.",
        "issuing_authority": "Insurance Company / Agriculture Department",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["farmer_name", "village", "crop", "insured_area", "sum_insured", "season"],
    },
    {
        "key": "soil_health_card",
        "name": "Soil Health Card",
        "category": "agriculture",
        "description": "Soil Health Card issued by agriculture department.",
        "issuing_authority": "Ministry of Agriculture, State Agriculture Department",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["farmer_name", "village", "survey_number", "issue_date"],
    },

    # ─── EDUCATION ────────────────────────────────────────────────────────────

    {
        "key": "educational_certificate",
        "name": "Educational / Degree Certificate",
        "category": "other",
        "description": "Degree, diploma, or educational certificate from recognized institution.",
        "issuing_authority": "University / Educational Institution / Board",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["student_name", "institution_name", "degree", "specialization", "year_of_passing", "roll_number"],
    },
    {
        "key": "marksheet",
        "name": "Marksheet / Result Card",
        "category": "other",
        "description": "Official marksheet from board or university examination.",
        "issuing_authority": "University / State Board / CBSE / ICSE",
        "is_ovi": False,
        "is_opa": False,
        "common_fields": ["student_name", "board_name", "exam_year", "marks_obtained"],
    },
]


# Build a quick-lookup dictionary keyed by "key"
DOCUMENT_TYPE_MAP: dict[str, DocumentType] = {doc["key"]: doc for doc in DOCUMENT_TYPES}

# Group by category
DOCUMENTS_BY_CATEGORY: dict[str, list[DocumentType]] = {}
for doc in DOCUMENT_TYPES:
    cat = doc["category"]
    DOCUMENTS_BY_CATEGORY.setdefault(cat, []).append(doc)


def get_document_by_key(key: str) -> DocumentType | None:
    return DOCUMENT_TYPE_MAP.get(key)


def get_documents_by_category(category: str) -> list[DocumentType]:
    return DOCUMENTS_BY_CATEGORY.get(category, [])
