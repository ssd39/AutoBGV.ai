# 07 — Quick-Start Workflow Templates

> 6 pre-built workflow templates covering the most common Indian KYC/verification use cases.
> Source: `services/workflow/app/constants/templates.py`

---

## Template 1: Basic Individual KYC

**Key**: `basic_individual_kyc`  
**Category**: KYC  
**Documents**: 3 | **Questions**: 3 | **Timeout**: 30 min

**Use case**: Standard individual KYC per RBI KYC Master Directions for account opening, onboarding.

### Documents
| Document | Required | Key Criteria |
|----------|----------|-------------|
| Aadhaar Card | ✅ | Not masked, name matches, not a photocopy |
| PAN Card | ✅ | Valid, name matches Aadhaar |
| Recent Address Proof (Utility Bill) | ✅ | Not older than 3 months, address matches |

### Questions
1. Is your Aadhaar address the same as current residential address? *(Yes/No)*
2. Are you a Politically Exposed Person (PEP)? *(Yes/No)*
3. What is your primary source of income? *(Multiple Choice)*
   - Salary / Employment
   - Business / Self-Employed
   - Investments / Rental Income
   - Pension / Retirement
   - Other

---

## Template 2: Home Loan Application KYC

**Key**: `home_loan_kyc`  
**Category**: Loan  
**Documents**: 8 | **Questions**: 4 | **Timeout**: 60 min

**Use case**: Comprehensive document collection for home loan applications at banks/NBFCs.

### Documents
| Document | Required | Key Criteria |
|----------|----------|-------------|
| Aadhaar Card | ✅ | Name matches loan application, both sides |
| PAN Card | ✅ | Valid, name matches Aadhaar |
| Passport | ❌ | NRI applicants only, not expired |
| Salary Slips (3 months) | ✅ | Last 3 months, stamped by employer |
| Form 16 (Latest) | ✅ | Latest financial year, issued by employer |
| Bank Statement (6 months) | ✅ | Salary account, bank stamped |
| Property Sale Agreement | ✅ | Registered, applicant name matches |
| Property Tax Receipt | ❌ | Latest, shows property address |

### Questions
1. What is your employment type? *(Multiple Choice)*
   - Salaried - Private Sector
   - Salaried - Government / PSU
   - Self-Employed Professional
   - Self-Employed Business
   - NRI
2. Approximate monthly gross income (INR)? *(Number)*
3. Property status? *(Multiple Choice)*
   - Ready to Move In (Resale)
   - Ready to Move In (New)
   - Under Construction
   - Plot Purchase
4. Do you have existing EMIs or outstanding loans? *(Yes/No)*

---

## Template 3: Insurance Claim Document Verification

**Key**: `insurance_claim`  
**Category**: Insurance  
**Documents**: 6 | **Questions**: 4 | **Timeout**: 45 min

**Use case**: Health/life insurance claim verification for faster claim processing.

### Documents
| Document | Required | Key Criteria |
|----------|----------|-------------|
| Aadhaar Card (Claimant) | ✅ | Must match policy records |
| Insurance Policy Document | ✅ | Active at time of claim, policy number matches |
| Hospital Bills (Original) | ✅ | From treatment period, itemized, original/certified |
| Hospital Discharge Summary | ✅ | Issued by treating hospital, doctor signed + stamped |
| Diagnostic Reports & Prescriptions | ❌ | From treatment period |
| Bank Account Details | ✅ | Cancelled cheque, IFSC visible, in claimant's name |

### Questions
1. What type of claim is this? *(Multiple Choice)*
   - Health Insurance - Hospitalization
   - Health Insurance - Day Care
   - Life Insurance - Death Claim
   - Accidental Claim
   - Critical Illness Claim
2. Was hospitalization planned or emergency? *(Multiple Choice)*
3. Total claimed amount (INR)? *(Number)*
4. Is claimant same as insured? *(Multiple Choice)*
   - Insured Person (Self)
   - Nominee / Legal Heir
   - Dependent Family Member

---

## Template 4: Business / MSME KYC

**Key**: `business_kyc`  
**Category**: KYC  
**Documents**: 7 | **Questions**: 3 | **Timeout**: 60 min

**Use case**: Entity KYC for business accounts, MSME loans, corporate onboarding.

### Documents
| Document | Required | Key Criteria |
|----------|----------|-------------|
| GST Registration Certificate | ✅ | Active, name matches registration |
| Certificate of Incorporation | ✅ | CoI (Pvt Ltd) / Partnership Deed / Udyam |
| Udyam / MSME Registration | ❌ | Optional for MSMEs |
| Business PAN Card | ✅ | In entity name, active |
| Business Bank Statement (12 months) | ✅ | Current account, bank stamped |
| Audited Financial Statements | ✅ | Last 2 years, CA certified, UDIN mentioned |
| Aadhaar (Authorized Signatory) | ✅ | Of majority director / authorized signatory |

### Questions
1. Legal structure of business? *(Multiple Choice)*
   - Sole Proprietorship
   - Partnership Firm
   - LLP
   - Private Limited Company
   - Public Limited Company
   - NGO / Trust / Society
2. Years in operation? *(Multiple Choice)*
3. Approximate annual turnover (INR)? *(Number)*

---

## Template 5: Vehicle Loan KYC

**Key**: `vehicle_loan_kyc`  
**Category**: Loan  
**Documents**: 5 | **Questions**: 2 | **Timeout**: 30 min

**Use case**: Quick KYC for two-wheeler and four-wheeler loan applications.

### Documents
| Document | Required | Key Criteria |
|----------|----------|-------------|
| Aadhaar Card | ✅ | Name matches, both sides |
| PAN Card | ✅ | Valid |
| Driving License | ✅ | Valid, not expired, relevant vehicle class |
| Salary Slip (3 months) | ✅ | Recent, employer signed |
| Bank Statement (6 months) | ✅ | Salary account |

### Questions
1. Vehicle type? *(Multiple Choice)*
   - Two-Wheeler
   - Four-Wheeler (Hatchback/Sedan)
   - Four-Wheeler (SUV/MUV)
   - Commercial Vehicle
2. New or used vehicle? *(Multiple Choice)*

---

## Template 6: Employment Background Verification (BGV)

**Key**: `employment_bgv`  
**Category**: Background Check  
**Documents**: 5 | **Questions**: 4 | **Timeout**: 30 min

**Use case**: Pre-employment background check covering identity, education, and employment history.

### Documents
| Document | Required | Key Criteria |
|----------|----------|-------------|
| Aadhaar Card | ✅ | — |
| PAN Card | ✅ | — |
| Highest Qualification Certificate | ✅ | From recognized institution, matches CV |
| Final Year Marksheet | ✅ | — |
| Previous Appointment Letter | ❌ | Most recent employer, shows designation |

### Questions
1. Total years of work experience? *(Number, 0–50)*
2. Ever terminated for misconduct? *(Yes/No)*
3. Any pending criminal cases? *(Yes/No)*
4. All CV details accurately represented? *(Yes/No)*

---

## How Templates Work

```
1. Client clicks "Use Template" on template_key
   ↓
2. POST /api/v1/workflows/templates/{template_key}/use
   ↓
3. Workflow Service clones the template into client's account
   - Sets status = "draft"
   - Copies all documents with their criteria
   - Copies all questions with their options
   ↓
4. Client edits the cloned workflow (can add/remove docs, change criteria)
   ↓
5. Client activates the workflow
   ↓
6. Client initiates sessions
```

## Adding New Templates

To add a new template, edit:
```python
# services/workflow/app/constants/templates.py

WORKFLOW_TEMPLATES.append({
    "template_key": "your_unique_key",
    "name": "Template Display Name",
    "description": "What this template is for",
    "category": "kyc",  # kyc|loan|insurance|background_check|property|business|custom
    "welcome_message": "Hello! ...",
    "completion_message": "Thank you! ...",
    "max_retry_attempts": 3,
    "session_timeout_minutes": 45,
    "documents": [...],
    "questions": [...]
})
```
