export type UserRole = 'user' | 'lawyer' | 'admin'

export interface User {
  id: number
  username: string
  role: UserRole
  display_name: string
  phone: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface CaseItem {
  id: number
  owner_id: number
  assigned_lawyer_id: number | null
  title: string
  dispute_type: string
  legal_relationship: string
  stage: string
  status: string
  location: string
  facts: string
  summary: string
  classification: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface MessageItem {
  id: number
  role: 'user' | 'assistant'
  content: string
  metadata_json: Record<string, unknown>
  created_at: string
}

export interface ConsultationResponse {
  case: CaseItem
  user_message: MessageItem
  assistant_message: MessageItem
  classification: {
    dispute_type: string
    dispute_label: string
    legal_relationship: string
    signals: string[]
  }
  structured: {
    intent: string
    dispute_label: string
    legal_relationship: string
    summary: string
    suggested_next_step: string
    required_information: string[]
    evidence_gaps: string[]
    risk_flags: string[]
    citations: string[]
    demo_mode: boolean
  }
  suggested_next_step: string
  demo_mode: boolean
}

export interface EvidenceItem {
  id: number
  case_id: number
  filename: string
  content_type: string
  file_size: number
  sha256: string
  category: string
  screening_status: string
  assessment: Record<string, unknown>
  created_at: string
}

export interface EvidenceResponse {
  items: EvidenceItem[]
  assessment: {
    status: string
    required_categories: string[]
    present_categories: string[]
    missing_categories: string[]
    missing_labels: string[]
    message: string
    disclaimer: string
  }
}

export interface ContractReviewResponse {
  risk_level: 'low' | 'medium' | 'high'
  findings: Array<{
    level: 'info' | 'medium' | 'high'
    title: string
    detail: string
  }>
  missing_items: string[]
  disclaimer: string
}

export interface DocumentItem {
  id: number
  case_id: number
  doc_type: string
  title: string
  content: string
  status: string
  version: number
  created_at: string
}

export type WorkflowStageStatus = 'completed' | 'current' | 'available' | 'locked'

export interface WorkflowStage {
  stage: string
  label: string
  status: WorkflowStageStatus
  required_actions: string[]
}

export interface WorkflowOption {
  target_stage: string
  label: string
  description: string
  enabled: boolean
  blocked_reasons: string[]
}

export interface WorkflowResponse {
  case_id: number
  current_stage: string
  stages: WorkflowStage[]
  options: WorkflowOption[]
}

export interface TransitionRequest {
  target_stage: string
  note?: string
}
