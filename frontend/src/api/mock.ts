import type {
  CaseItem,
  EvidenceResponse,
  WorkflowOption,
  WorkflowResponse,
  WorkflowStage,
} from '../types/api'

// 阶段 1 前端 Mock：workflow / transitions 后端尚未实现（契约中标记「计划中」）。
// 这里按接口契约用本地演示规则生成固定结构，字段名与枚举值必须和契约一致。
// 后端实现后，删除本文件，改回直接调用 apiRequest('/cases/{id}/workflow')。

const STAGE_ORDER = [
  'intake',
  'evidence',
  'procedure',
  'document',
  'lawyer_help',
  'closed',
] as const

const STAGE_LABELS: Record<string, string> = {
  intake: '识别问题',
  evidence: '整理证据',
  procedure: '协商或仲裁',
  document: '文书准备',
  lawyer_help: '律师协助',
  closed: '已结案',
}

export function buildWorkflowResponse(
  caseItem: CaseItem,
  assessment: EvidenceResponse['assessment'] | null,
): WorkflowResponse {
  const currentStage = caseItem.stage
  const currentIndex = Math.max(
    0,
    STAGE_ORDER.indexOf(currentStage as (typeof STAGE_ORDER)[number]),
  )
  const missingLabels = assessment?.missing_labels ?? []
  const evidenceReady = assessment ? assessment.missing_categories.length === 0 : false

  const stages: WorkflowStage[] = STAGE_ORDER.map((stage, index) => {
    let status: WorkflowStage['status']
    if (index < currentIndex) {
      status = 'completed'
    } else if (index === currentIndex) {
      status = 'current'
    } else {
      status = 'locked'
    }

    let requiredActions: string[] = []
    if (stage === 'evidence') {
      requiredActions = missingLabels
    } else if (stage === 'procedure') {
      requiredActions = evidenceReady ? [] : ['确认证据是否充分']
    }

    return { stage, label: STAGE_LABELS[stage], status, required_actions: requiredActions }
  })

  const options: WorkflowOption[] = []
  if (currentStage === 'evidence') {
    options.push({
      target_stage: 'procedure',
      label: '进入协商或仲裁',
      description: '证据齐全后可进入协商或仲裁程序。',
      enabled: evidenceReady,
      blocked_reasons: evidenceReady ? [] : missingLabels,
    })
  } else if (currentStage === 'procedure') {
    options.push({
      target_stage: 'document',
      label: '生成仲裁文书',
      description: '基于已确认事实生成仲裁申请书草稿。',
      enabled: true,
      blocked_reasons: [],
    })
  } else if (currentStage === 'document') {
    options.push({
      target_stage: 'lawyer_help',
      label: '申请律师协助',
      description: '由本站律师进行人工复核与协助。',
      enabled: true,
      blocked_reasons: [],
    })
  }

  return {
    case_id: caseItem.id,
    current_stage: currentStage,
    stages,
    options,
  }
}
