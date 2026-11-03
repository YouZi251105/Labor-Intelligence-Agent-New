<template>
  <section v-if="caseItem" class="content-page case-detail-page">
    <header class="case-detail-header">
      <button class="back-button" type="button" @click="goBackToList">
        <ArrowLeft :size="18" />
      </button>
      <div class="case-detail-header__main">
        <span class="eyebrow">案件 #{{ caseItem.id }}</span>
        <h1>{{ caseItem.title }}</h1>
        <div class="tag-row">
          <span class="status-tag">{{ dictionary.disputeLabels[caseItem.dispute_type] || '待识别' }}</span>
          <span class="status-tag">{{ dictionary.stageLabels[caseItem.stage] || caseItem.stage }}</span>
          <span class="status-tag">
            {{ caseItem.legal_relationship === 'service' ? '劳务关系' : '劳动关系' }}
          </span>
          <span v-if="caseItem.assigned_lawyer_id" class="status-tag status-tag--success">
            已分配律师
          </span>
        </div>
      </div>
      <button v-if="!auth.isLawyer" class="secondary-action" type="button" @click="router.push('/')">继续 AI 咨询</button>
    </header>

    <nav class="tab-bar" aria-label="案件功能">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <component :is="tab.icon" :size="17" />
        {{ tab.label }}
      </button>
    </nav>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section v-if="activeTab === 'overview'">
      <div
        v-if="activeRequest && ['accepted', 'in_session'].includes(activeRequest.status)"
        class="session-banner"
      >
        <span>
          {{ activeRequest.status === 'accepted' ? '律师已受理你的预约' : '正在与律师咨询中' }}，可以在「律师协助」页签继续对话。
        </span>
        <button class="primary-action primary-action--compact" type="button" @click="activeTab = 'lawyer'">
          进入对话
        </button>
      </div>
      <div v-if="workflow" class="detail-card workflow-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">案件流程</span>
            <h2>{{ workflowLabel }}</h2>
          </div>
          <span
            class="status-tag"
            :class="{ 'status-tag--warning': workflow.rule_package.review_status === 'pending_review' }"
          >
            {{ workflowReviewLabel }}
          </span>
        </div>
        <ol class="workflow-steps">
          <li
            v-for="stage in workflow.stages"
            :key="stage.stage"
            :class="`workflow-step workflow-step--${stage.status}`"
          >
            <span class="workflow-step__dot" />
            <div class="workflow-step__body">
              <strong>{{ stage.label }}</strong>
              <small v-if="stage.required_actions.length">
                待办：{{ stage.required_actions.join('、') }}
              </small>
            </div>
          </li>
        </ol>
        <div v-if="workflow.options.length" class="workflow-options">
          <article
            v-for="option in workflow.options"
            :key="option.id"
            class="workflow-option"
            :class="{ 'workflow-option--blocked': !option.enabled }"
          >
            <div class="workflow-option__heading">
              <strong>{{ option.label }}</strong>
              <span v-if="option.deadlines.some((item) => item.review_status === 'pending_review')">
                含待复核期限
              </span>
            </div>
            <p>{{ option.description }}</p>
            <dl class="workflow-option__details">
              <div>
                <dt>选择后</dt>
                <dd>{{ option.outcome }}</dd>
              </div>
              <div>
                <dt>下一步</dt>
                <dd>{{ option.next_step }}</dd>
              </div>
            </dl>
            <div v-if="option.deadlines.length" class="workflow-deadlines">
              <article v-for="deadline in option.deadlines" :key="deadline.id">
                <strong>{{ deadline.title }}</strong>
                <p>{{ deadline.description }}</p>
                <small v-if="deadline.due_at">
                  建议截止：{{ new Date(deadline.due_at).toLocaleDateString('zh-CN') }}
                </small>
                <small v-else>期限规则{{ reviewStatusLabel(deadline.review_status) }}</small>
              </article>
            </div>
            <p
              v-if="!option.enabled"
              class="workflow-option__reason workflow-option__reason--blocked"
            >
              {{ option.blocked_reasons.join('；') }}
            </p>
            <button
              class="secondary-action workflow-option__action"
              type="button"
              :disabled="!option.enabled || transitioningTarget === option.id"
              @click="transitionTo(option)"
            >
              {{ transitioningTarget === option.id ? '处理中...' : option.label }}
            </button>
          </article>
        </div>
        <small class="workflow-disclaimer">{{ workflow.rule_package.disclaimer }}</small>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <span class="eyebrow">案件事实</span>
          <p class="pre-line">{{ caseItem.facts || '暂无案件事实' }}</p>
        </div>
        <div class="detail-card">
          <span class="eyebrow">当前建议</span>
          <p>{{ suggestedNextStep || '继续补充咨询信息，系统会更新案件建议。' }}</p>
          <dl class="meta-list">
            <div><dt>用工地点</dt><dd>{{ caseItem.location || '待补充' }}</dd></div>
            <div><dt>更新时间</dt><dd>{{ new Date(caseItem.updated_at).toLocaleString('zh-CN') }}</dd></div>
            <div><dt>承办律师</dt><dd>{{ caseItem.assigned_lawyer_id ? '已分配' : '尚未分配' }}</dd></div>
          </dl>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'chat'" class="detail-card detail-card--wide">
      <div class="detail-section-heading">
        <div>
          <span class="eyebrow">咨询记录</span>
          <h2>多轮案件咨询</h2>
        </div>
        <span class="status-tag">{{ messages.length }} 条消息</span>
      </div>
      <div class="case-chat-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="chat-message"
          :class="`chat-message--${message.role}`"
        >
          <span class="chat-message__role">{{ message.role === 'user' ? '你' : '劳务通' }}</span>
          <SafeMarkdown :content="message.content" />
        </article>
        <p v-if="!messages.length" class="muted-text">还没有咨询记录。</p>
      </div>
      <form v-if="!auth.isLawyer" class="chat-compose-inline" @submit.prevent="sendChat">
        <textarea v-model="chatInput" rows="3" placeholder="继续补充事实，系统会带上当前案件上下文。" />
        <button class="primary-action primary-action--compact" type="submit" :disabled="chatSending">
          {{ chatSending ? '发送中...' : '发送' }}
        </button>
      </form>
      <p v-else class="muted-text">你以承办律师身份查看咨询记录，仅当事人可以继续对话。</p>
    </section>

    <section v-else-if="activeTab === 'evidence'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">材料上传</span>
        <h2>证据整理</h2>
        <p>演示版支持图片、PDF、TXT、DOC 和 DOCX，单文件不超过 20MB。</p>
        <label v-if="!auth.isLawyer" class="upload-zone">
          <Upload :size="24" />
          <strong>{{ uploading ? '正在上传...' : '选择证据材料' }}</strong>
          <span>上传后会自动分类并生成材料缺口提示</span>
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.doc,.docx" @change="uploadEvidence" />
        </label>

        <div v-if="evidenceRulesAssessment" class="rules-assessment">
          <div class="detail-section-heading">
            <div>
              <span class="eyebrow">证据四性评估</span>
              <h2>材料评估</h2>
            </div>
          </div>
          <div
            class="dimension-card"
            :class="`dimension--${evidenceRulesAssessment.completeness.status === 'ready' ? 'ok' : 'warning'}`"
          >
            <strong>完整性</strong>
            <span>
              {{ evidenceRulesAssessment.completeness.status === 'ready' ? '材料类别已覆盖' : '仍有缺口' }}
            </span>
            <p v-if="evidenceRulesAssessment.completeness.missing_labels.length">
              缺少：{{ evidenceRulesAssessment.completeness.missing_labels.join('、') }}
            </p>
            <p v-if="evidenceRulesAssessment.completeness.present_categories.length">
              已有：{{
                evidenceRulesAssessment.completeness.present_categories
                  .map((item) => dictionary.categoryLabels[item] || item)
                  .join('、')
              }}
            </p>
          </div>
          <div
            v-for="dim in dimensions"
            :key="dim.key"
            class="dimension-card"
            :class="`dimension--${dim.status}`"
          >
            <strong>{{ dim.label }}</strong>
            <span>{{ dimStatusLabel(dim.status) }}</span>
            <p v-for="finding in dim.findings" :key="finding.message">{{ finding.message }}</p>
          </div>
          <small class="muted-text">{{ evidenceRulesAssessment.disclaimer }}</small>
        </div>
      </div>
      <div class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">材料列表</span>
            <h2>{{ evidenceItems.length }} 份材料</h2>
          </div>
        </div>
        <div class="evidence-list">
          <article v-for="item in evidenceItems" :key="item.id">
            <FileText :size="19" />
            <div class="evidence-list__main">
              <strong>{{ item.filename }}</strong>
              <span>{{ dictionary.categoryLabels[item.category] || item.category }} · {{ formatFileSize(item.file_size) }}</span>
              <small class="evidence-list__time">上传于 {{ new Date(item.created_at).toLocaleString('zh-CN') }}</small>
            </div>
            <div class="evidence-list__side">
              <span class="status-tag" :class="`extract-${item.extraction_status}`">
                {{ extractionStatusLabels[item.extraction_status] || item.extraction_status }}
              </span>
              <div class="row-actions">
                <button type="button" @click="previewEvidence(item)">查看</button>
                <button type="button" :disabled="extractingId === item.id" @click="extractEvidence(item)">
                  {{ extractingId === item.id ? '提取中...' : '重新提取' }}
                </button>
                <button type="button" @click="downloadEvidence(item)">下载</button>
                <button
                  type="button"
                  class="row-actions__danger"
                  :disabled="deletingId === item.id"
                  @click="deleteEvidence(item)"
                >
                  {{ deletingId === item.id ? '删除中...' : '删除' }}
                </button>
              </div>
            </div>
          </article>
          <p v-if="!evidenceItems.length" class="muted-text">还没有上传材料。</p>
        </div>
      </div>

      <div v-if="preview" class="preview-modal" @click.self="closePreview">
        <div class="preview-modal__body">
          <img v-if="preview.isImage" :src="preview.url" :alt="preview.filename" />
          <pre v-else class="preview-modal__text">{{ preview.text }}</pre>
          <button type="button" class="preview-modal__close" @click="closePreview">关闭</button>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'contract'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">合同审查</span>
        <h2>粘贴合同内容</h2>
        <p>演示版基于文本规则识别明显风险，不构成合同真实性或法律效力结论。</p>
        <textarea
          v-model="contractText"
          class="large-textarea"
          rows="10"
          placeholder="粘贴合同条款，例如工资、工作时间、解除条件和社会保险约定……"
        />
        <button class="primary-action primary-action--compact" type="button" :disabled="reviewing" @click="reviewContract">
          {{ reviewing ? '审查中...' : '开始审查' }}
        </button>
        <div v-if="contractReview" class="review-result">
          <span class="status-tag" :class="`risk-${contractReview.risk_level}`">
            风险等级：{{ riskLabels[contractReview.risk_level] }}
          </span>
          <article v-for="finding in contractReview.findings" :key="finding.title">
            <strong>{{ finding.title }}</strong>
            <p>{{ finding.detail }}</p>
          </article>
          <p v-if="contractReview.missing_items.length">
            建议补充：{{ contractReview.missing_items.join('、') }}
          </p>
          <small>{{ contractReview.disclaimer }}</small>
        </div>
      </div>
      <div class="detail-card">
        <span class="eyebrow">文件审查</span>
        <h2>上传合同文件</h2>
        <p>支持 TXT、PDF、DOCX 和图片，系统会先提取文本再审查。</p>
        <label class="upload-zone">
          <Upload :size="24" />
          <strong>{{ reviewingFile ? '正在审查...' : '选择合同文件' }}</strong>
          <span>上传后自动提取文本并做风险提示</span>
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.doc,.docx" @change="reviewContractFile" />
        </label>
        <div v-if="contractFileReview" class="review-result">
          <span class="status-tag" :class="`extract-${contractFileReview.extraction_status}`">
            {{ extractionStatusLabels[contractFileReview.extraction_status] || contractFileReview.extraction_status }}
          </span>
          <span class="status-tag" :class="`risk-${contractFileReview.review.risk_level}`">
            风险等级：{{ riskLabels[contractFileReview.review.risk_level] }}
          </span>
          <article v-for="finding in contractFileReview.review.findings" :key="finding.title">
            <strong>{{ finding.title }}</strong>
            <p>{{ finding.detail }}</p>
          </article>
          <p v-if="contractFileReview.review.missing_items.length">
            建议补充：{{ contractFileReview.review.missing_items.join('、') }}
          </p>
          <small>{{ contractFileReview.review.disclaimer }}</small>
        </div>
        <div class="manual-review-entry">
          <ShieldCheck :size="16" />
          <span>风险判断需要专业复核？</span>
          <RouterLink to="/help" class="text-link">申请人工复核</RouterLink>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'documents'" class="detail-grid">
      <div v-if="!auth.isLawyer" class="detail-card">
        <span class="eyebrow">文书生成</span>
        <h2>生成案件草稿</h2>
        <p>系统会根据已确认的案件事实和证据目录生成文本草稿。</p>
        <div class="document-actions">
          <button
            v-for="option in documentOptions"
            :key="option.type"
            class="secondary-action"
            type="button"
            :disabled="generatingDocument === option.type"
            @click="generateDocument(option.type)"
          >
            <FilePlus2 :size="17" />
            {{ option.label }}
          </button>
        </div>
      </div>
      <div class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">草稿列表</span>
            <h2>{{ documents.length }} 份文书</h2>
          </div>
        </div>
        <div class="document-list">
          <article v-for="document in documents" :key="document.id">
            <div>
              <strong>{{ document.title }}</strong>
              <span>版本 {{ document.version }} · {{ new Date(document.created_at).toLocaleString('zh-CN') }}</span>
              <small v-if="document.evidence.length">引用 {{ document.evidence.length }} 份证据</small>
            </div>
            <div class="row-actions">
              <button type="button" @click="selectedDocument = document">预览</button>
              <button type="button" @click="startEditDocument(document)">编辑</button>
              <button type="button" :disabled="exportingFormat !== ''" @click="exportDocument(document, 'docx')">DOCX</button>
              <button type="button" :disabled="exportingFormat !== ''" @click="exportDocument(document, 'pdf')">PDF</button>
              <button type="button" @click="downloadDocument(document)">TXT</button>
            </div>
          </article>
          <p v-if="!documents.length" class="muted-text">还没有生成文书。</p>
        </div>
      </div>
      <div v-if="editingDocument" class="detail-card detail-card--wide">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">编辑文书</span>
            <h2>保存为新版本</h2>
          </div>
        </div>
        <div class="form-grid">
          <div class="form-grid__wide">
            <label>
              标题
              <input v-model="editTitle" />
            </label>
          </div>
          <div class="form-grid__wide">
            <label>
              内容
              <textarea v-model="editContent" rows="12" />
            </label>
          </div>
        </div>
        <div class="form-actions">
          <button class="primary-action primary-action--compact" type="button" :disabled="savingRevision" @click="saveRevision">
            {{ savingRevision ? '保存中...' : '保存为新版本' }}
          </button>
          <button class="secondary-action" type="button" @click="editingDocument = null">取消</button>
        </div>
      </div>
      <div v-if="selectedDocument" class="detail-card detail-card--wide">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">文书预览</span>
            <h2>{{ selectedDocument.title }}</h2>
          </div>
          <button class="secondary-action" type="button" @click="selectedDocument = null">关闭</button>
        </div>
        <SafeMarkdown class="document-preview" :content="selectedDocument.content" />
      </div>
    </section>

    <section v-else-if="activeTab === 'lawyer'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">被动介入</span>
        <h2>预约律师协助</h2>
        <p>复杂问题可预约律师人工介入；律师受理后进入专属咨询对话，记录会留存供双方随时查看。</p>
        <template v-if="activeRequest">
          <div class="lawyer-request-status">
            <span class="status-tag" :class="{ 'status-tag--warning': activeRequest.priority === 'urgent' }">
              {{ requestStatusLabel(activeRequest.status) }}
            </span>
            <span v-if="activeRequest.priority === 'urgent'" class="status-tag status-tag--warning">加急</span>
          </div>
          <ol class="lawyer-progress">
            <li
              v-for="step in requestProgress"
              :key="step.label"
              class="lawyer-progress__step"
              :class="`lawyer-progress__step--${step.state}`"
            >
              <span class="lawyer-progress__dot">
                <CircleCheck v-if="step.state === 'done'" :size="12" />
              </span>
              <small>{{ step.label }}</small>
            </li>
          </ol>
          <p class="pre-line">{{ activeRequest.reason }}</p>
          <p v-if="slaExpired" class="lawyer-slot-warning">
            已超出承诺受理时限（{{ slaHours }} 小时），律师会尽快处理；如有急事可取消后重新预约或联系平台。
          </p>
          <p v-else-if="requestExpired" class="lawyer-slot-warning">
            已超过期望时间，律师会尽快与你联系；如有急事可取消后重新预约加急时段。
          </p>
          <small v-else-if="activeRequest.status === 'pending'" class="muted-text">
            预计受理时限：{{ slaHours }} 小时内 · 受理后按所选时段开始回复
          </small>
          <p v-if="activeRequest.status === 'rejected' && activeRequest.reject_reason" class="lawyer-slot-warning">
            律师说明：{{ activeRequest.reject_reason }}
          </p>
          <small class="muted-text">
            期望时间：{{ requestTimeText(activeRequest) }} · 提交于
            {{ new Date(activeRequest.created_at).toLocaleString('zh-CN') }}
          </small>
          <div
            v-if="activeRequest.status === 'pending' || activeRequest.status === 'accepted'"
            class="form-actions"
          >
            <button class="secondary-action" type="button" :disabled="cancellingRequest" @click="cancelRequest">
              {{ cancellingRequest ? '取消中...' : '取消预约' }}
            </button>
          </div>
        </template>
        <form v-else class="lawyer-request-form" @submit.prevent="createRequest">
          <div class="lawyer-form-block">
            <span class="lawyer-form-block__title">1 · 描述问题</span>
            <textarea
              v-model="requestForm.reason"
              rows="6"
              required
              placeholder="例如：公司拒不支付赔偿，材料已备齐，想请律师判断是否可以申请仲裁。"
            />
          </div>
          <div class="lawyer-form-block">
            <span class="lawyer-form-block__title">2 · 选择时间（可选）</span>
            <div class="lawyer-date-grid">
              <button
                v-for="option in dateOptions"
                :key="option.iso"
                type="button"
                class="lawyer-date-chip"
                :class="{ 'lawyer-date-chip--active': requestForm.preferred_date === option.iso }"
                @click="requestForm.preferred_date = requestForm.preferred_date === option.iso ? '' : option.iso"
              >
                <small>{{ option.badge }}</small>
                <strong>{{ option.monthDay }}</strong>
              </button>
            </div>
            <div v-if="requestForm.preferred_date" class="lawyer-slot-picker">
              <span class="lawyer-slot-picker__label">期望时段</span>
              <div class="lawyer-slot-picker__options">
                <button
                  v-for="option in slotOptions"
                  :key="option.value"
                  type="button"
                  class="lawyer-slot-chip"
                  :class="{ 'lawyer-slot-chip--active': requestForm.preferred_slot === option.value }"
                  @click="requestForm.preferred_slot = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>
          </div>
          <div class="lawyer-form-block">
            <span class="lawyer-form-block__title">3 · 紧急程度</span>
            <div class="lawyer-slot-picker__options">
              <button
                v-for="option in priorityOptions"
                :key="option.value"
                type="button"
                class="lawyer-slot-chip"
                :class="{ 'lawyer-slot-chip--active': requestForm.priority === option.value }"
                @click="requestForm.priority = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
          <div class="form-actions">
            <button
              class="primary-action primary-action--compact"
              type="submit"
              :disabled="creatingRequest || !requestForm.reason.trim()"
            >
              {{ creatingRequest ? '提交中...' : '提交预约' }}
            </button>
          </div>
        </form>
      </div>

      <div class="detail-card">
        <span class="eyebrow">主动介入</span>
        <h2>立案前人工复核</h2>
        <p v-if="!caseReview">
          案件准备仲裁或网上立案前，可申请律师复核最终材料，判断是否具备立案条件，避免盲目走流程。
        </p>
        <button
          v-if="!caseReview"
          class="secondary-action"
          type="button"
          :disabled="requestingReview"
          @click="requestReview"
        >
          {{ requestingReview ? '申请中...' : '申请立案前复核' }}
        </button>
        <div v-else-if="!reviewVerdict" class="lawyer-review-result">
          <span class="status-tag status-tag--warning">复核进行中，律师会尽快处理</span>
          <small class="muted-text">
            申请于 {{ new Date(caseReview.created_at).toLocaleString('zh-CN') }}
          </small>
        </div>
        <template v-else>
          <div class="review-verdict" :class="`review-verdict--${reviewVerdict.tone}`">
            <component :is="reviewVerdict.icon" :size="20" />
            <div>
              <strong>{{ reviewVerdict.labels.title }}</strong>
              <p>{{ reviewVerdict.labels.description }}</p>
            </div>
          </div>
          <p v-if="reviewVerdict.comment" class="pre-line lawyer-review-comment">
            律师意见：{{ reviewVerdict.comment }}
          </p>
          <div class="lawyer-next-step">
            <span class="lawyer-next-step__title">选择后续方式</span>
            <p v-if="!caseReview.user_decision" class="muted-text">
              复核已完成，请选择接下来由谁完成立案等正式流程（之后可以更改）。
            </p>
            <div class="lawyer-next-step__options">
              <button
                v-for="option in (['self_handle', 'lawyer_assist'] as ReviewUserDecision[])"
                :key="option"
                type="button"
                class="lawyer-slot-chip"
                :class="{ 'lawyer-slot-chip--active': caseReview.user_decision === option }"
                :disabled="submittingDecision"
                @click="submitDecision(option)"
              >
                {{ decisionLabels[option] }}
              </button>
            </div>
            <p v-if="reviewNextStep">{{ reviewNextStep }}</p>
          </div>
          <small class="muted-text">
            复核时间：{{ new Date(reviewVerdict.at).toLocaleString('zh-CN') }}
          </small>
        </template>
      </div>

      <div v-if="caseSession" class="detail-card detail-card--wide">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">律师咨询</span>
            <h2>与律师的对话</h2>
          </div>
          <span class="status-tag" :class="{ 'status-tag--success': caseSession.status === 'active' }">
            {{ caseSession.status === 'active' ? '进行中' : '已结束' }}
          </span>
        </div>
        <ConsultationChat :session="caseSession" sender-role="user" @closed="onSessionClosed" />
      </div>
    </section>
  </section>

  <div v-else class="loading-block"><span class="spinner-dot" /> 正在加载案件...</div>
</template>

<script setup lang="ts">
import {
  ArrowLeft,
  CircleCheck,
  CircleX,
  Clock3,
  FilePlus2,
  FileText,
  MessageSquareText,
  Scale,
  ShieldCheck,
  TriangleAlert,
  Upload,
  UserCheck,
} from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { API_BASE_URL, ApiError, apiRequest, TOKEN_KEY } from '../api/http'
import ConsultationChat from '../components/ConsultationChat.vue'
import SafeMarkdown from '../components/SafeMarkdown.vue'
import type {
  CaseItem,
  CaseReviewItem,
  ConsultationResponse,
  ConsultationSessionItem,
  ContractFileReviewResponse,
  ContractReviewResponse,
  DocumentItem,
  EvidenceAssessmentResponse,
  EvidenceExtractionResponse,
  EvidenceItem,
  EvidenceResponse,
  LawyerRequestItem,
  MessageItem,
  RequestSlot,
  ReviewUserDecision,
  WorkflowOption,
  WorkflowResponse,
} from '../types/api'
import { formatFileSize } from '../utils/format'
import { useAuthStore } from '../stores/auth'
import { useDictionaryStore } from '../stores/dictionary'
import { confirmAction, notifySuccess } from '../utils/dialogs'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const caseId = Number(route.params.id)
const caseItem = ref<CaseItem | null>(null)
const messages = ref<MessageItem[]>([])
const evidenceItems = ref<EvidenceItem[]>([])
const evidenceAssessment = ref<EvidenceResponse['assessment'] | null>(null)
const documents = ref<DocumentItem[]>([])
const activeTab = ref('overview')
const error = ref('')
const suggestedNextStep = ref('')
const chatInput = ref('')
const chatSending = ref(false)
const uploading = ref(false)
const contractText = ref('')
const reviewing = ref(false)
const contractReview = ref<ContractReviewResponse | null>(null)
const generatingDocument = ref('')
const selectedDocument = ref<DocumentItem | null>(null)
const workflow = ref<WorkflowResponse | null>(null)
const transitioningTarget = ref('')
const evidenceRulesAssessment = ref<EvidenceAssessmentResponse | null>(null)
const extractingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
const preview = ref<{ filename: string; isImage: boolean; url: string; text: string } | null>(null)
const contractFileReview = ref<ContractFileReviewResponse | null>(null)
const reviewingFile = ref(false)
const editingDocument = ref<DocumentItem | null>(null)
const editTitle = ref('')
const editContent = ref('')
const savingRevision = ref(false)
const exportingFormat = ref('')

const lawyerRequests = ref<LawyerRequestItem[]>([])
const caseSessions = ref<ConsultationSessionItem[]>([])
const caseReview = ref<CaseReviewItem | null>(null)
const creatingRequest = ref(false)
const cancellingRequest = ref(false)
const requestingReview = ref(false)
const requestForm = reactive({
  reason: '',
  preferred_date: '',
  preferred_slot: 'evening' as RequestSlot,
  priority: 'normal' as 'normal' | 'urgent',
})

const requestSlotLabels: Record<RequestSlot, string> = {
  morning: '上午 09:00-12:00',
  afternoon: '下午 14:00-18:00',
  evening: '晚间 18:00-21:00',
}
const slotOptions = (Object.keys(requestSlotLabels) as RequestSlot[]).map((value) => ({
  value,
  label: requestSlotLabels[value],
}))
const priorityOptions = [
  { value: 'normal' as const, label: '一般' },
  { value: 'urgent' as const, label: '加急' },
]

function localIso(day: Date) {
  const y = day.getFullYear()
  const m = String(day.getMonth() + 1).padStart(2, '0')
  const d = String(day.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const dateMin = localIso(new Date())
const dateOptions = computed(() => {
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return Array.from({ length: 15 }, (_, offset) => {
    const day = new Date()
    day.setDate(day.getDate() + offset)
    return {
      iso: localIso(day),
      monthDay: `${day.getMonth() + 1}月${day.getDate()}日`,
      badge: offset === 0 ? '今天' : offset === 1 ? '明天' : weekdays[day.getDay()],
    }
  })
})

const requestStatusLabels: Record<string, string> = {
  pending: '待律师受理',
  accepted: '律师已受理',
  rejected: '律师未受理',
  in_session: '咨询中',
  completed: '已完成',
  cancelled: '已取消',
}
const reviewConclusionLabels: Record<string, { title: string; description: string }> = {
  ready_to_file: {
    title: '材料齐备，可以立案',
    description: '律师认为当前材料和事实足以进入仲裁或诉讼程序。',
  },
  need_more: {
    title: '需要补充材料后再立案',
    description: '还有关键材料缺失，建议按律师意见补充后再申请。',
  },
  not_recommended: {
    title: '暂不建议立案',
    description: '当前条件下立案风险较高，建议先协商或采取其他方式维权。',
  },
}

const activeRequest = computed(
  () =>
    lawyerRequests.value.find((item) =>
      ['pending', 'accepted', 'in_session'].includes(item.status),
    ) ?? null,
)
const caseSession = computed(() => caseSessions.value[0] ?? null)

type ProgressState = 'done' | 'current' | 'todo'
interface ProgressStep {
  label: string
  state: ProgressState
}

const requestProgress = computed<ProgressStep[]>(() => {
  const status = activeRequest.value?.status
  const labels = ['提交预约', '律师受理', '咨询对话', '预约完成']
  const reached =
    status === 'completed'
      ? 4
      : status === 'in_session'
        ? 3
        : status === 'accepted'
          ? 2
          : status === 'pending'
            ? 1
            : 0
  const terminal = status === 'rejected' || status === 'cancelled'
  return labels.map((label, index) => ({
    label,
    state: (index < reached
      ? 'done'
      : index === reached && !terminal
        ? 'current'
        : 'todo') as ProgressState,
  }))
})

const reviewVerdict = computed(() => {
  const review = caseReview.value
  if (!review || review.status !== 'reviewed' || !review.conclusion) return null
  const map = {
    ready_to_file: { icon: CircleCheck, tone: 'success' },
    need_more: { icon: TriangleAlert, tone: 'warning' },
    not_recommended: { icon: CircleX, tone: 'danger' },
  } as const
  const meta = map[review.conclusion]
  return {
    icon: meta.icon,
    tone: meta.tone,
    labels: reviewConclusionLabels[review.conclusion],
    comment: review.comment,
    at: review.reviewed_at ?? review.created_at,
  }
})

const slaHours = computed(() => (activeRequest.value?.priority === 'urgent' ? 2 : 24))
const slaExpired = computed(() => {
  const request = activeRequest.value
  if (!request || request.status !== 'pending') return false
  const deadline = new Date(request.created_at).getTime() + slaHours.value * 3_600_000
  return Date.now() > deadline
})

const decisionLabels: Record<ReviewUserDecision, string> = {
  self_handle: '自己完成后续流程',
  lawyer_assist: '需要律师协助',
}
const submittingDecision = ref(false)

async function submitDecision(decision: ReviewUserDecision) {
  const review = caseReview.value
  if (!review) return
  submittingDecision.value = true
  error.value = ''
  try {
    const updated = await apiRequest<CaseReviewItem>(
      `/lawyer-service/reviews/${review.id}/decision`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      },
    )
    caseReview.value = updated
    notifySuccess(decision === 'self_handle' ? '已记录：自行办理后续流程' : '已记录：继续由律师协助')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '选择提交失败'
  } finally {
    submittingDecision.value = false
  }
}

const reviewNextStep = computed(() => {
  const decision = caseReview.value?.user_decision
  if (decision === 'self_handle') {
    return '已选择自行办理。可在「法律文书」页签生成或下载仲裁申请书，携带证据原件前往仲裁机构办理；办理中遇到问题随时回来预约律师。'
  }
  if (decision === 'lawyer_assist') {
    return activeRequest.value
      ? '已选择律师协助。可在上方对话框与律师继续沟通，或按提示完成预约。'
      : '已选择律师协助。请在上方提交预约，律师会尽快受理并与你对话。'
  }
  return ''
})

function requestStatusLabel(status: string) {
  return requestStatusLabels[status] ?? status
}

function goBackToList() {
  router.push(auth.isLawyer ? '/lawyer' : '/cases')
}

async function fetchReview(): Promise<CaseReviewItem | null> {
  try {
    return await apiRequest<CaseReviewItem>(`/lawyer-service/cases/${caseId}/review`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

async function loadLawyerService() {
  if (auth.user?.role !== 'user') return
  try {
    const [requests, sessions] = await Promise.all([
      apiRequest<LawyerRequestItem[]>('/lawyer-service/requests'),
      apiRequest<ConsultationSessionItem[]>('/lawyer-service/sessions'),
    ])
    lawyerRequests.value = requests.filter((item) => item.case_id === caseId)
    caseSessions.value = sessions.filter((item) => item.case_id === caseId)
    caseReview.value = await fetchReview()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '律师服务数据加载失败'
  }
}

async function createRequest() {
  const reason = requestForm.reason.trim()
  if (!reason) return
  creatingRequest.value = true
  error.value = ''
  try {
    const created = await apiRequest<LawyerRequestItem>('/lawyer-service/requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: caseId,
        reason,
        preferred_date: requestForm.preferred_date || null,
        preferred_slot: requestForm.preferred_date ? requestForm.preferred_slot : null,
        priority: requestForm.priority,
      }),
    })
    lawyerRequests.value.unshift(created)
    requestForm.reason = ''
    requestForm.preferred_date = ''
    requestForm.preferred_slot = 'evening'
    requestForm.priority = 'normal'
    notifySuccess('预约已提交，律师会尽快处理')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '预约提交失败'
  } finally {
    creatingRequest.value = false
  }
}

function requestTimeText(request: LawyerRequestItem) {
  if (request.preferred_date && request.preferred_slot) {
    const monthDay = request.preferred_date.slice(5).replace('-', '月')
    return `${monthDay}日 · ${requestSlotLabels[request.preferred_slot]}`
  }
  return request.preferred_time || '不限'
}

const requestExpired = computed(() => {
  const request = activeRequest.value
  if (!request) return false
  if (!['pending', 'accepted'].includes(request.status)) return false
  return Boolean(request.preferred_date && request.preferred_date < dateMin)
})

async function cancelRequest() {
  if (!activeRequest.value) return
  const confirmed = await confirmAction('确认取消该律师服务预约？', {
    title: '取消预约',
    confirmText: '确认取消',
  })
  if (!confirmed) return
  cancellingRequest.value = true
  error.value = ''
  try {
    await apiRequest(`/lawyer-service/requests/${activeRequest.value.id}/cancel`, {
      method: 'POST',
    })
    await loadLawyerService()
    notifySuccess('预约已取消')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '预约取消失败'
  } finally {
    cancellingRequest.value = false
  }
}

function onSessionClosed(closed: ConsultationSessionItem) {
  const index = caseSessions.value.findIndex((item) => item.id === closed.id)
  if (index >= 0) caseSessions.value[index] = closed
  void loadLawyerService()
}

async function requestReview() {
  requestingReview.value = true
  error.value = ''
  try {
    caseReview.value = await apiRequest<CaseReviewItem>(`/lawyer-service/cases/${caseId}/review`, {
      method: 'POST',
    })
    notifySuccess('复核申请已提交，律师会尽快处理')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '复核申请失败'
  } finally {
    requestingReview.value = false
  }
}

const tabs = computed(() => {
  const base = [
    { key: 'overview', label: '案件概览', icon: Scale },
    { key: 'chat', label: '咨询记录', icon: MessageSquareText },
    { key: 'evidence', label: '证据材料', icon: Upload },
    { key: 'contract', label: '合同审查', icon: FileText },
    { key: 'documents', label: '法律文书', icon: FilePlus2 },
  ]
  if (auth.user?.role === 'user') {
    base.push({ key: 'lawyer', label: '律师协助', icon: UserCheck })
  }
  return base
})
const dictionary = useDictionaryStore()
const documentOptions = [
  { type: 'settlement', label: '协商和解协议' },
  { type: 'arbitration', label: '劳动仲裁申请书' },
  { type: 'complaint', label: '民事起诉状' },
] as const
const riskLabels = { low: '低', medium: '中', high: '高' }

const extractionStatusLabels: Record<string, string> = {
  pending: '待提取',
  extracted: '已提取',
  ocr_required: '待 OCR',
  unsupported: '不支持',
  failed: '提取失败',
}

function dimStatusLabel(status: string) {
  if (status === 'ok') return '正常'
  if (status === 'warning') return '需关注'
  if (status === 'issue') return '需复核'
  return status
}

const latestClassification = computed(() => caseItem.value?.classification ?? {})

const dimensions = computed(() => {
  const rules = evidenceRulesAssessment.value
  if (!rules) return []
  return [
    {
      key: 'legality',
      label: '合法性（形式）',
      status: rules.legality.status,
      findings: rules.legality.findings,
    },
    {
      key: 'relevance',
      label: '关联性',
      status: rules.relevance.status,
      findings: rules.relevance.findings,
    },
    {
      key: 'sufficiency',
      label: '充分性',
      status: rules.sufficiency.status,
      findings: rules.sufficiency.findings,
    },
  ]
})

const workflowLabel = computed(() => {
  if (!workflow.value) return '案件流程'
  const current = workflow.value.stages.find(
    (item) => item.stage === workflow.value?.current_stage,
  )
  return current?.label ?? '案件流程'
})

const workflowReviewLabel = computed(() => {
  const status = workflow.value?.rule_package.review_status
  return status === 'pending_review' ? '规则待复核' : reviewStatusLabel(status ?? '')
})

function reviewStatusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: '草稿',
    pending_review: '待复核',
    approved: '已批准',
    published: '已发布',
    retired: '已停用',
    rejected: '已驳回',
  }
  return labels[status] ?? status
}

async function loadAll() {
  try {
    const [caseData, messageData, evidenceData, documentData, workflowData, rulesAssessment] =
      await Promise.all([
        apiRequest<CaseItem>(`/cases/${caseId}`),
        apiRequest<MessageItem[]>(`/cases/${caseId}/messages`),
        apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`),
        apiRequest<DocumentItem[]>(`/cases/${caseId}/documents`),
        apiRequest<WorkflowResponse>(`/cases/${caseId}/workflow`),
        apiRequest<EvidenceAssessmentResponse>(`/cases/${caseId}/evidence-assessment`),
      ])
    caseItem.value = caseData
    messages.value = messageData
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
    documents.value = documentData
    workflow.value = workflowData
    evidenceRulesAssessment.value = rulesAssessment
    suggestedNextStep.value = String(
      messageData.at(-1)?.metadata_json?.suggested_next_step ??
        caseItem.value.classification.suggested_next_step ??
        '',
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  }
}

async function transitionTo(option: WorkflowOption) {
  if (!caseItem.value) return
  transitioningTarget.value = option.id
  error.value = ''
  try {
    workflow.value = await apiRequest<WorkflowResponse>(`/cases/${caseId}/transitions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ option_id: option.id }),
    })
    caseItem.value = {
      ...caseItem.value,
      stage: workflow.value.current_stage,
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件阶段推进失败'
  } finally {
    transitioningTarget.value = ''
  }
}

async function sendChat() {
  const text = chatInput.value.trim()
  if (!text) return
  chatSending.value = true
  try {
    const response = await apiRequest<ConsultationResponse>(`/cases/${caseId}/consultations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
    messages.value.push(response.user_message, response.assistant_message)
    caseItem.value = response.case
    suggestedNextStep.value = response.suggested_next_step
    workflow.value = await apiRequest<WorkflowResponse>(`/cases/${caseId}/workflow`)
    chatInput.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    chatSending.value = false
  }
}

async function uploadEvidence(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    await apiRequest<EvidenceItem>(`/cases/${caseId}/evidence`, {
      method: 'POST',
      body,
    })
    const evidenceData = await apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`)
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
    evidenceRulesAssessment.value = await apiRequest<EvidenceAssessmentResponse>(
      `/cases/${caseId}/evidence-assessment`,
    )
    workflow.value = await apiRequest<WorkflowResponse>(`/cases/${caseId}/workflow`)
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

async function reviewContract() {
  if (!contractText.value.trim()) return
  reviewing.value = true
  try {
    contractReview.value = await apiRequest<ContractReviewResponse>(
      `/cases/${caseId}/contract-review`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: contractText.value }),
      },
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '合同审查失败'
  } finally {
    reviewing.value = false
  }
}

async function generateDocument(type: 'settlement' | 'arbitration' | 'complaint') {
  generatingDocument.value = type
  try {
    const document = await apiRequest<DocumentItem>(`/cases/${caseId}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_type: type }),
    })
    documents.value.unshift(document)
    selectedDocument.value = document
  } catch (err) {
    error.value = err instanceof Error ? err.message : '文书生成失败'
  } finally {
    generatingDocument.value = ''
  }
}

async function downloadDocument(documentItem: DocumentItem) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/documents/${documentItem.id}/download`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
      },
    },
  )
  if (!response.ok) {
    error.value = '文书下载失败'
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${documentItem.title}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

async function extractEvidence(item: EvidenceItem) {
  extractingId.value = item.id
  error.value = ''
  try {
    await apiRequest<EvidenceExtractionResponse>(
      `/cases/${caseId}/evidence/${item.id}/extract`,
      { method: 'POST' },
    )
    const evidenceData = await apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`)
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
  } catch (err) {
    error.value = err instanceof Error ? err.message : '重新提取失败'
  } finally {
    extractingId.value = null
  }
}

async function downloadEvidence(item: EvidenceItem) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/evidence/${item.id}/download`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
      },
    },
  )
  if (!response.ok) {
    error.value = '材料下载失败'
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = item.filename
  link.click()
  URL.revokeObjectURL(url)
}

async function deleteEvidence(item: EvidenceItem) {
  const confirmed = await confirmAction(
    `确认删除材料“${item.filename}”？删除后不可恢复。`,
    {
      title: '删除材料',
      confirmText: '删除',
      danger: true,
    },
  )
  if (!confirmed) return
  deletingId.value = item.id
  error.value = ''
  try {
    await apiRequest(`/cases/${caseId}/evidence/${item.id}`, { method: 'DELETE' })
    if (preview.value?.filename === item.filename) closePreview()
    const evidenceData = await apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`)
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
    evidenceRulesAssessment.value = await apiRequest<EvidenceAssessmentResponse>(
      `/cases/${caseId}/evidence-assessment`,
    )
    notifySuccess('材料已删除')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    deletingId.value = null
  }
}

async function previewEvidence(item: EvidenceItem) {
  const isImage = item.content_type.startsWith('image/')
  if (isImage) {
    const response = await fetch(
      `${API_BASE_URL}/cases/${caseId}/evidence/${item.id}/download`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
        },
      },
    )
    if (!response.ok) {
      error.value = '预览加载失败'
      return
    }
    const blob = await response.blob()
    preview.value = {
      filename: item.filename,
      isImage: true,
      url: URL.createObjectURL(blob),
      text: '',
    }
  } else {
    preview.value = {
      filename: item.filename,
      isImage: false,
      url: '',
      text: item.text_preview || '该类型暂不支持在线预览，请点击「下载」查看。',
    }
  }
}

function closePreview() {
  if (preview.value?.url) URL.revokeObjectURL(preview.value.url)
  preview.value = null
}

async function reviewContractFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  reviewingFile.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    contractFileReview.value = await apiRequest<ContractFileReviewResponse>(
      `/cases/${caseId}/contract-review/file`,
      { method: 'POST', body },
    )
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '合同文件审查失败'
  } finally {
    reviewingFile.value = false
  }
}

function startEditDocument(documentItem: DocumentItem) {
  editingDocument.value = documentItem
  editTitle.value = documentItem.title
  editContent.value = documentItem.content
}

async function saveRevision() {
  if (!editingDocument.value) return
  savingRevision.value = true
  error.value = ''
  try {
    const revision = await apiRequest<DocumentItem>(
      `/cases/${caseId}/documents/${editingDocument.value.id}/revisions`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle.value.trim(),
          content: editContent.value,
        }),
      },
    )
    documents.value = await apiRequest<DocumentItem[]>(`/cases/${caseId}/documents`)
    selectedDocument.value = revision
    editingDocument.value = null
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存版本失败'
  } finally {
    savingRevision.value = false
  }
}

async function exportDocument(documentItem: DocumentItem, format: 'docx' | 'pdf') {
  exportingFormat.value = format
  error.value = ''
  try {
    const response = await fetch(
      `${API_BASE_URL}/cases/${caseId}/documents/${documentItem.id}/export?format=${format}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
        },
      },
    )
    if (!response.ok) {
      error.value = '导出失败'
      return
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${documentItem.title}.${format}`
    link.click()
    URL.revokeObjectURL(url)
  } finally {
    exportingFormat.value = ''
  }
}

onMounted(async () => {
  await dictionary.load()
  await loadAll()
  await loadLawyerService()
})
</script>
