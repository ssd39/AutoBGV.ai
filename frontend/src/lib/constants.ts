import { DocumentCategory, WorkflowCategory, WorkflowStatus } from '@/types';

export const CLIENT_ID = process.env.NEXT_PUBLIC_CLIENT_ID || 'client_001';

export const WORKFLOW_SERVICE_URL =
  process.env.NEXT_PUBLIC_WORKFLOW_SERVICE_URL || 'http://localhost:8001';

// ─── Category Labels & Colors ─────────────────────────────────────────────────

export const CATEGORY_CONFIG: Record<WorkflowCategory, { label: string; color: string; bg: string; icon: string }> = {
  kyc:              { label: 'KYC',               color: 'text-blue-700',   bg: 'bg-blue-50',   icon: '🪪' },
  loan:             { label: 'Loan',              color: 'text-green-700',  bg: 'bg-green-50',  icon: '🏦' },
  insurance:        { label: 'Insurance',         color: 'text-purple-700', bg: 'bg-purple-50', icon: '🛡️' },
  background_check: { label: 'Background Check',  color: 'text-orange-700', bg: 'bg-orange-50', icon: '🔍' },
  property:         { label: 'Property',          color: 'text-yellow-700', bg: 'bg-yellow-50', icon: '🏠' },
  business:         { label: 'Business',          color: 'text-teal-700',   bg: 'bg-teal-50',   icon: '🏢' },
  custom:           { label: 'Custom',            color: 'text-gray-700',   bg: 'bg-gray-50',   icon: '⚙️' },
};

export const STATUS_CONFIG: Record<WorkflowStatus, { label: string; color: string; bg: string; dot: string }> = {
  draft:    { label: 'Draft',    color: 'text-gray-600',   bg: 'bg-gray-100',   dot: 'bg-gray-400'   },
  active:   { label: 'Active',   color: 'text-green-700',  bg: 'bg-green-100',  dot: 'bg-green-500'  },
  inactive: { label: 'Inactive', color: 'text-yellow-700', bg: 'bg-yellow-100', dot: 'bg-yellow-500' },
  archived: { label: 'Archived', color: 'text-red-700',    bg: 'bg-red-100',    dot: 'bg-red-400'    },
};

export const DOC_CATEGORY_CONFIG: Record<DocumentCategory, { label: string; color: string; bg: string; icon: string }> = {
  identity:    { label: 'Identity',    color: 'text-blue-700',   bg: 'bg-blue-50',   icon: '🪪' },
  address:     { label: 'Address',     color: 'text-green-700',  bg: 'bg-green-50',  icon: '🏠' },
  income:      { label: 'Income',      color: 'text-purple-700', bg: 'bg-purple-50', icon: '💰' },
  business:    { label: 'Business',    color: 'text-teal-700',   bg: 'bg-teal-50',   icon: '🏢' },
  property:    { label: 'Property',    color: 'text-yellow-700', bg: 'bg-yellow-50', icon: '🏗️' },
  vehicle:     { label: 'Vehicle',     color: 'text-orange-700', bg: 'bg-orange-50', icon: '🚗' },
  medical:     { label: 'Medical',     color: 'text-red-700',    bg: 'bg-red-50',    icon: '🏥' },
  agriculture: { label: 'Agriculture', color: 'text-lime-700',   bg: 'bg-lime-50',   icon: '🌾' },
  other:       { label: 'Other',       color: 'text-gray-700',   bg: 'bg-gray-50',   icon: '📄' },
};

export const QUESTION_TYPE_CONFIG = {
  text:            { label: 'Open Text',        icon: '📝' },
  yes_no:          { label: 'Yes / No',         icon: '✅' },
  multiple_choice: { label: 'Multiple Choice',  icon: '📋' },
  number:          { label: 'Number',           icon: '🔢' },
  date:            { label: 'Date',             icon: '📅' },
};

// ─── Document Category Order for display ──────────────────────────────────────

export const DOCUMENT_CATEGORY_ORDER: DocumentCategory[] = [
  'identity',
  'address',
  'income',
  'business',
  'property',
  'vehicle',
  'medical',
  'agriculture',
  'other',
];

// ─── Nav Items ────────────────────────────────────────────────────────────────

export const NAV_ITEMS = [
  { href: '/',           label: 'Dashboard',  icon: 'LayoutDashboard' },
  { href: '/workflows',  label: 'Workflows',  icon: 'GitBranch'       },
  { href: '/sessions',   label: 'Sessions',   icon: 'Play'            },
  { href: '/analytics',  label: 'Analytics',  icon: 'BarChart2'       },
  { href: '/settings',   label: 'Settings',   icon: 'Settings'        },
];

// ─── Default values ───────────────────────────────────────────────────────────

export const DEFAULT_ALLOWED_FORMATS = ['jpg', 'jpeg', 'png', 'pdf'];
export const DEFAULT_MAX_FILE_SIZE_MB = 10;
