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

export type ExtractionStatus = 'pending' | 'extracted' | 'ocr_required' | 'unsupported' | 'failed'

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
  text_preview: string
  extraction_status: ExtractionStatus
  extraction_message: string
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

export interface DocumentEvidenceItem {
  evidence_id: number
  filename: string
  category: string
  sha256: string
}

export interface DocumentItem {
  id: number
  case_id: number
  doc_type: string
  title: string
  content: string
  status: string
  version: number
  evidence: DocumentEvidenceItem[]
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

export interface EvidenceExtractionResponse {
  evidence_id: number
  extraction_status: ExtractionStatus
  extracted_text: string
  message: string
}

export interface ContractFileReviewResponse {
  filename: string
  extraction_status: ExtractionStatus
  extracted_text: string
  review: ContractReviewResponse
}

export interface DocumentRevisionCreate {
  title: string
  content: string
  status?: 'draft'
}

export interface AssessmentFinding {
  level: string
  message: string
}

export interface AssessmentDimension {
  status: string
  findings: AssessmentFinding[]
}

export interface CompletenessAssessment {
  status: 'ready' | 'needs_more'
  required_categories: string[]
  present_categories: string[]
  missing_categories: string[]
  missing_labels: string[]
}

export interface EvidenceAssessmentResponse {
  case_id: number
  dispute_type: string
  legality: AssessmentDimension
  relevance: AssessmentDimension
  sufficiency: AssessmentDimension
  completeness: CompletenessAssessment
  disclaimer: string
}

export type SimulationRole = 'boss' | 'hr' | 'arbitrator' | 'judge' | 'lawyer'

export interface SimulationScore {
  clarity: number
  evidence_awareness: number
  legal_appropriateness: number
  overall: number
  suggestions: string[]
}

export interface SimulationMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  score: SimulationScore | null
  created_at: string
}

export interface SimulationSession {
  id: number
  case_id: number
  user_id: number
  role_type: SimulationRole
  scenario: string
  status: string
  created_at: string
  updated_at: string
}

export interface SimulationSessionDetail extends SimulationSession {
  messages: SimulationMessage[]
}

export interface SimulationReply {
  session: SimulationSession
  user_message: SimulationMessage
  assistant_message: SimulationMessage
  score: SimulationScore
}

export interface HelpResource {
  id: number
  resource_type: string
  name: string
  region: string
  address: string
  website: string
  phone: string
  description: string
  status: string
  created_at: string
}

export interface SiteLawyer {
  id: number
  display_name: string
  specialties: string
  bio: string
  status: string
}

export interface TopicSummary {
  dispute_type: string
  label: string
  count: number
}

export interface TopicsResponse {
  topics: TopicSummary[]
  total: number
}

export interface HistoryCaseSummary {
  case_id: number
  title: string
  dispute_type: string
  stage: string
  summary: string
  updated_at: string
}

export interface HistoryResponse {
  cases: HistoryCaseSummary[]
}

export interface LawyerOpinion {
  id: number
  case_id: number
  lawyer_id: number
  content: string
  status: string
  created_at: string
}

export interface ServiceRecord {
  id: number
  case_id: number
  lawyer_id: number
  service_type: string
  summary: string
  duration_minutes: number
  status: string
  occurred_at: string
  created_at: string
}

export interface RevenueLedger {
  id: number
  lawyer_id: number
  case_id: number | null
  service_record_id: number | null
  amount_cents: number
  entry_type: string
  status: string
  note: string
  created_at: string
}

export interface MaterialSummary {
  id: number
  case_id: number
  filename: string
  content_type: string
  file_size: number
  category: string
  screening_status: string
  extraction_status: string
  created_at: string
}

export interface AuditLogItem {
  id: number
  actor_id: number | null
  action: string
  object_type: string
  object_id: number
  metadata_json: Record<string, unknown>
  created_at: string
}

export interface RuleConfigItem {
  id: number
  dispute_type: string
  name: string
  evidence_requirements: string[]
  next_steps: string[]
  source_note: string
  review_status: string
  version: number
  created_at: string
  updated_at: string
}

export interface UserProfileItem {
  user_id: number
  real_name: string
  phone: string
  id_number_masked: string
  verification_status: 'unverified' | 'pending' | 'verified' | 'rejected'
  created_at: string
  updated_at: string
}
