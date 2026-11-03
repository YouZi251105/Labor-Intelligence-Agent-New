<template>
  <details v-if="visibleReferences.length" class="reference-materials">
    <summary>
      <BookOpen :size="16" />
      参考资料（{{ visibleReferences.length }}）
    </summary>
    <div class="reference-materials__body">
      <section v-if="laws.length">
        <h3><Scale :size="15" />法律依据</h3>
        <article v-for="item in laws" :key="`law-${item.id}`">
          <strong>{{ item.title }}</strong>
          <p v-if="item.excerpt">{{ item.excerpt }}</p>
          <p class="reference-materials__meta">
            <span>{{ item.source_name || '来源待补充' }}</span>
            <a
              v-if="safeUrl(item.source_url)"
              :href="safeUrl(item.source_url)"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看来源
            </a>
          </p>
        </article>
      </section>
      <section v-if="cases.length">
        <h3><BriefcaseBusiness :size="15" />相关类案</h3>
        <article v-for="item in cases" :key="`case-${item.id}`">
          <strong>{{ item.title }}</strong>
          <p v-if="item.excerpt">{{ item.excerpt }}</p>
          <p class="reference-materials__meta">
            <span v-if="item.case_no">{{ item.case_no }}</span>
            <span v-if="item.court">{{ item.court }}</span>
            <a
              v-if="safeUrl(item.source_url)"
              :href="safeUrl(item.source_url)"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看来源
            </a>
          </p>
        </article>
      </section>
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen, BriefcaseBusiness, Scale } from '@lucide/vue'

import type { ReferenceItem } from '../types/api'

const props = defineProps<{
  references: ReferenceItem[]
}>()

const approvedStatuses = new Set(['approved', 'published'])
const visibleReferences = computed(() =>
  props.references.filter(
    (item) =>
      (item.type === 'law' || item.type === 'case') &&
      approvedStatuses.has(item.review_status),
  ),
)
const laws = computed(() =>
  visibleReferences.value.filter((item) => item.type === 'law'),
)
const cases = computed(() =>
  visibleReferences.value.filter((item) => item.type === 'case'),
)

function safeUrl(value: string | undefined): string {
  if (!value) return ''
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : ''
  } catch {
    return ''
  }
}
</script>

<style scoped>
.reference-materials {
  margin-top: 14px;
  border-top: 1px solid var(--border-soft, #e5e7eb);
  color: var(--text-secondary, #4b5563);
  font-size: 13px;
}

.reference-materials summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 2px 4px;
  color: var(--text-secondary, #4b5563);
  cursor: pointer;
  user-select: none;
}

.reference-materials__body {
  display: grid;
  gap: 12px;
  padding: 8px 0 2px;
}

.reference-materials__body section {
  display: grid;
  gap: 8px;
}

.reference-materials__body h3 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--text-primary, #1f2937);
  font-size: 13px;
}

.reference-materials__body article {
  padding: 10px 12px;
  border: 1px solid var(--border-soft, #e5e7eb);
  border-radius: 8px;
  background: var(--surface-subtle, #f9fafb);
}

.reference-materials__body p {
  margin: 5px 0 0;
  line-height: 1.55;
}

.reference-materials__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  color: var(--text-muted, #6b7280);
  font-size: 12px;
}

.reference-materials__meta a {
  color: var(--accent-strong, #9e1b1b);
  text-decoration: none;
}
</style>
