# 06 — Indian Document Catalog

> Complete registry of 52 document types supported by AutoBGV.
> Source: `services/workflow/app/constants/documents.py`

**Legend**: OVI = Officially Valid Identity (PMLA), OPA = Officially Valid Address Proof

---

## 🪪 Identity Documents (7)

| Key | Name | Issuing Authority | OVI | OPA |
|-----|------|-------------------|-----|-----|
| `aadhaar_card` | Aadhaar Card | UIDAI | ✅ | ✅ |
| `pan_card` | PAN Card | Income Tax Dept. | ✅ | ❌ |
| `passport` | Passport | Ministry of External Affairs | ✅ | ✅ |
| `voter_id` | Voter ID Card (EPIC) | Election Commission | ✅ | ✅ |
| `driving_license` | Driving License | Regional Transport Authority | ✅ | ✅ |
| `nrega_job_card` | NREGA Job Card | Ministry of Rural Development | ✅ | ❌ |
| `digilocker_aadhaar` | DigiLocker Aadhaar | UIDAI via DigiLocker | ✅ | ✅ |

**Common fields**: aadhaar_number / pan_number / passport_number, name, dob, photo, address

---

## 🏠 Address Proof Documents (7)

| Key | Name | Issuing Authority | OVI | OPA |
|-----|------|-------------------|-----|-----|
| `electricity_bill` | Electricity Bill (≤3 months) | State Electricity Board | ❌ | ✅ |
| `water_bill` | Water / Municipal Bill | Municipal Corporation | ❌ | ✅ |
| `gas_connection_bill` | Gas Connection Bill | IGL / MGL etc. | ❌ | ✅ |
| `telephone_bill` | Telephone / Broadband Bill | Telecom Provider | ❌ | ✅ |
| `bank_statement_address` | Bank Statement (Address Proof) | Scheduled Bank | ❌ | ✅ |
| `rent_agreement` | Rent / Lease Agreement | Sub-Registrar Office | ❌ | ✅ |
| `property_tax_receipt` | Property Tax Receipt | Municipal Corporation | ❌ | ✅ |
| `ration_card` | Ration Card | State Food & Civil Supplies | ❌ | ✅ |

**Note**: All address proof documents must be dated within 3 months typically.

---

## 💰 Income / Financial Documents (7)

| Key | Name | Issuing Authority |
|-----|------|-------------------|
| `salary_slip` | Salary Slip (Last 3 months) | Employer / HR |
| `form_16` | Form 16 (TDS Certificate) | Employer |
| `itr_acknowledgement` | ITR Acknowledgement | Income Tax Dept. |
| `bank_statement_6months` | Bank Statement (6 Months) | Scheduled Bank |
| `bank_statement_12months` | Bank Statement (12 Months) | Scheduled Bank |
| `ca_certified_financials` | CA Certified Financial Statements | Chartered Accountant |
| `appointment_letter` | Employment Appointment Letter | Employer |

---

## 🏢 Business Documents (9)

| Key | Name | Issuing Authority | OPA |
|-----|------|-------------------|-----|
| `gst_certificate` | GST Registration Certificate | GSTN | ✅ |
| `certificate_of_incorporation` | Certificate of Incorporation | Registrar of Companies | ❌ |
| `moa` | Memorandum of Association | ROC / MCA | ❌ |
| `aoa` | Articles of Association | ROC / MCA | ❌ |
| `partnership_deed` | Partnership Deed | Sub-Registrar | ❌ |
| `msme_registration` | Udyam / MSME Registration | Ministry of MSME | ❌ |
| `trade_license` | Trade License | Municipal Corporation | ✅ |
| `shop_establishment_certificate` | Shop & Establishment Certificate | State Labour Dept. | ✅ |
| `board_resolution` | Board Resolution | Company Board | ❌ |

---

## 🏗️ Property Documents (7)

| Key | Name | Issuing Authority |
|-----|------|-------------------|
| `sale_deed` | Sale Deed / Agreement to Sale | Sub-Registrar Office |
| `encumbrance_certificate` | Encumbrance Certificate (EC) | Sub-Registrar |
| `property_tax_document` | Property Tax Paid Receipt | Municipal Corporation |
| `title_search_report` | Title Search Report | Advocate / Title Search Co. |
| `building_plan_approval` | Building Plan Approval | Municipal Corporation |
| `noc_society` | NOC from Housing Society | Registered Society |
| `khata_certificate` | Khata Certificate / Extract | BBMP / Municipal |

---

## 🚗 Vehicle Documents (3)

| Key | Name | Issuing Authority |
|-----|------|-------------------|
| `rc_book` | Registration Certificate (RC Book) | Regional Transport Office |
| `vehicle_insurance` | Vehicle Insurance Certificate | General Insurance Company |
| `puc_certificate` | PUC Certificate | Authorized PUC Centre |

---

## 🏥 Medical / Insurance Documents (6)

| Key | Name | Issuing Authority |
|-----|------|-------------------|
| `medical_reports` | Medical Reports / Health Records | Registered Hospital |
| `hospital_bills` | Hospital Bills / Medical Bills | Registered Hospital |
| `discharge_summary` | Discharge Summary | Registered Hospital |
| `previous_insurance_policy` | Previous Insurance Policy | IRDAI Licensed Insurer |
| `death_certificate` | Death Certificate | Municipal Corporation |
| `fir_copy` | FIR Copy (Police Report) | Police Station |

---

## 🌾 Agriculture Documents (4)

| Key | Name | Issuing Authority |
|-----|------|-------------------|
| `kisan_credit_card` | Kisan Credit Card | Scheduled Bank / NABARD |
| `land_records_7_12` | Land Records (7/12 Extract / RTC) | Talathi / Revenue Dept. |
| `crop_insurance_policy` | Crop Insurance Policy (PMFBY) | Insurance Co. / Agri Dept. |
| `soil_health_card` | Soil Health Card | Ministry of Agriculture |

---

## 📄 Other Documents (2)

| Key | Name | Issuing Authority |
|-----|------|-------------------|
| `educational_certificate` | Educational / Degree Certificate | University / Board |
| `marksheet` | Marksheet / Result Card | University / State Board |

---

## Common Fields Reference

| Field Key | Description |
|-----------|-------------|
| `aadhaar_number` | 12-digit Aadhaar UID |
| `pan_number` | 10-character alphanumeric PAN |
| `name` | Full name on document |
| `date_of_birth` | Date of birth |
| `address` | Registered address |
| `photo` | Photograph on document |
| `expiry_date` | Document expiry/validity date |
| `issue_date` | Document issue date |
| `issuing_authority` | Name of issuing authority |
| `signature` | Signature present |

---

## Criteria Parsing — Supported Patterns

The natural language criteria parser understands these patterns:

| Natural Language | Parsed Condition |
|-----------------|-----------------|
| "must not be expired" | `expiry_date > today` |
| "not older than 3 months" | `issue_date >= today - 3 months` |
| "name must match" | `name_match == applicant_name` |
| "both sides required" | `both_sides_provided == true` |
| "not a photocopy" | `document_type == original` |
| "address must match" | `address_match == application_address` |
| "photo must be visible" | `photo_present == true` |
| "must be signed by employer" | `signature_present == true` |
| "must be stamped by bank" | `stamp_present == true` |
| "pan must be valid" | `pan_status == active` |
| "gst must be active" | `gst_status == active` |
| "ifsc code" | `ifsc_present == true` |
| "clearly readable" | `legibility == clear` |

> **Note**: This is currently rule-based. Future: LLM integration for higher accuracy.
