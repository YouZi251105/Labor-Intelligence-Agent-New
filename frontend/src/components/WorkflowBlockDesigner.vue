<template>
  <div v-if="content" class="workflow-designer">
    <aside class="workflow-designer__palette">
      <span class="eyebrow">受控积木</span>
      <h3>流程组件</h3>
      <button
        v-for="item in palette"
        :key="item.type"
        type="button"
        class="workflow-palette__item"
        draggable="true"
        @dragstart="startPaletteDrag($event, item.type)"
        @click="addBlock(item.type, 40, nextAutoY)"
      >
        <component :is="item.icon" :size="17" />
        <span>
          <strong>{{ item.label }}</strong>
          <small>{{ item.description }}</small>
        </span>
      </button>
      <p class="workflow-designer__hint">
        积木可拖动到画布。连接目标从各出口的节点下拉框中选择。
      </p>
    </aside>

    <section
      class="workflow-designer__canvas"
      :style="{ minHeight: `${canvasHeight}px` }"
      @dragover.prevent
      @drop="dropOnCanvas"
    >
      <article
        v-for="block in designerBlocks"
        :key="block.id"
        class="workflow-block"
        :class="[
          `workflow-block--${block.block_type}`,
          { active: selectedBlockId === block.id },
        ]"
        :style="{ left: `${block.position.x}px`, top: `${block.position.y}px` }"
        @click="selectedBlockId = block.id"
      >
        <header
          class="workflow-block__header"
          draggable="true"
          @dragstart="startBlockDrag($event, block.id)"
        >
          <span class="workflow-block__kind">{{ blockTypeLabel(block.block_type) }}</span>
          <strong>{{ content.nodes[block.id]?.label || block.id }}</strong>
          <small>{{ block.id }} · {{ stageLabel(content.nodes[block.id]?.stage ?? '') }}</small>
        </header>
        <div class="workflow-block__ports">
          <div v-for="option in content.nodes[block.id]?.options ?? []" :key="option.id">
            <span>{{ option.label || '未命名出口' }}</span>
            <strong>{{ option.target_node || '未连接' }}</strong>
          </div>
          <small v-if="block.block_type === 'end'">流程结束，无输出</small>
        </div>
      </article>
      <p v-if="!designerBlocks.length" class="workflow-designer__empty">
        从左侧拖入第一个流程积木。
      </p>
    </section>

    <aside v-if="selectedBlock && selectedNode" class="workflow-designer__inspector">
      <div class="workflow-designer__inspector-heading">
        <div>
          <span class="eyebrow">积木设置</span>
          <h3>{{ selectedNode.label || selectedBlock.id }}</h3>
        </div>
        <button
          type="button"
          class="icon-button"
          title="删除积木"
          :disabled="selectedBlock.id === content.start_node"
          @click="removeBlock(selectedBlock.id)"
        >
          <Trash2 :size="16" />
        </button>
      </div>

      <label>
        <span>名称</span>
        <input v-model="selectedNode.label" @input="emitContent" />
      </label>
      <label>
        <span>业务阶段</span>
        <select v-model="selectedNode.stage" @change="changeStage">
          <option v-for="stage in content.stages" :key="stage.key" :value="stage.key">
            {{ stage.label }}
          </option>
        </select>
      </label>
      <label>
        <span>积木类型</span>
        <select
          :value="selectedBlock.block_type"
          @change="changeBlockType(($event.target as HTMLSelectElement).value as BlockType)"
        >
          <option v-for="item in palette" :key="item.type" :value="item.type">
            {{ item.label }}
          </option>
        </select>
      </label>

      <div v-if="selectedBlock.block_type !== 'end'" class="workflow-outlets">
        <div class="workflow-outlets__heading">
          <strong>出口与去向</strong>
          <button
            v-if="selectedBlock.block_type === 'decision'"
            type="button"
            class="table-action"
            @click="addOption"
          >
            <Plus :size="14" />
            增加出口
          </button>
        </div>
        <details
          v-for="(option, index) in selectedNode.options"
          :key="option.id"
          class="workflow-outlet"
          :open="index === 0"
        >
          <summary>
            <span>{{ option.label || `出口 ${index + 1}` }}</span>
            <strong>{{ option.target_node || '未连接' }}</strong>
          </summary>
          <label>
            <span>出口名称</span>
            <input v-model="option.label" @input="emitContent" />
          </label>
          <label>
            <span>目标积木</span>
            <select v-model="option.target_node" @change="changeTarget(option)">
              <option value="">未连接</option>
              <option
                v-for="target in connectableTargets"
                :key="target.id"
                :value="target.id"
              >
                {{ target.label }} · {{ target.id }}
              </option>
            </select>
          </label>
          <label>
            <span>选择后结果</span>
            <textarea v-model="option.outcome" rows="2" @input="emitContent" />
          </label>
          <label>
            <span>下一步操作</span>
            <textarea v-model="option.next_step" rows="2" @input="emitContent" />
          </label>
          <button
            v-if="selectedBlock.block_type === 'decision' && selectedNode.options.length > 2"
            type="button"
            class="table-action workflow-outlet__remove"
            @click="removeOption(option.id)"
          >
            删除此出口
          </button>
        </details>
      </div>
      <p v-else class="muted-text">结束块没有输出，也不能再连接到其他节点。</p>
    </aside>
  </div>
</template>

<script setup lang="ts">
import {
  CircleStop,
  FileCheck2,
  GitBranch,
  Plus,
  Scale,
  ShieldCheck,
  Trash2,
} from '@lucide/vue'
import { computed, ref, watch } from 'vue'

type BlockType = 'stage' | 'decision' | 'evidence_gate' | 'lawyer_gate' | 'end'

interface StageRule {
  key: string
  label: string
}

interface Requirement {
  type: string
  message?: string
}

interface OptionRule {
  id: string
  label: string
  description: string
  target_stage: string
  target_node: string
  outcome: string
  next_step: string
  requirements: Requirement[]
  deadlines: unknown[]
}

interface NodeRule {
  stage: string
  label: string
  options: OptionRule[]
}

interface BlockRule {
  id: string
  block_type: BlockType
  position: { x: number; y: number }
}

interface DesignerContent {
  start_node: string
  stages: StageRule[]
  nodes: Record<string, NodeRule>
  designer?: {
    version: 1
    blocks: BlockRule[]
  }
}

const props = defineProps<{
  modelValue: Record<string, unknown>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
}>()

const palette = [
  { type: 'stage' as const, label: '阶段块', description: '单一顺序出口', icon: Scale },
  { type: 'decision' as const, label: '选择块', description: '多个可选路径', icon: GitBranch },
  {
    type: 'evidence_gate' as const,
    label: '证据条件块',
    description: '满足与不满足分支',
    icon: FileCheck2,
  },
  {
    type: 'lawyer_gate' as const,
    label: '律师条件块',
    description: '已分配与未分配分支',
    icon: ShieldCheck,
  },
  { type: 'end' as const, label: '结束块', description: '当前路径终点', icon: CircleStop },
]

const content = ref<DesignerContent | null>(null)
const selectedBlockId = ref('')
const draggingBlockId = ref('')
let optionCounter = 0

watch(
  () => props.modelValue,
  (value) => {
    content.value = normalizeContent(value)
    if (JSON.stringify(content.value) !== JSON.stringify(value)) {
      emit('update:modelValue', content.value as unknown as Record<string, unknown>)
    }
    if (!selectedBlockId.value || !content.value.nodes[selectedBlockId.value]) {
      selectedBlockId.value = content.value.start_node
    }
  },
  { immediate: true, deep: true },
)

const designerBlocks = computed(() => content.value?.designer?.blocks ?? [])
const selectedBlock = computed(() =>
  designerBlocks.value.find((item) => item.id === selectedBlockId.value),
)
const selectedNode = computed(() =>
  selectedBlock.value && content.value
    ? content.value.nodes[selectedBlock.value.id]
    : null,
)
const nextAutoY = computed(() => 40 + designerBlocks.value.length * 230)
const canvasHeight = computed(() =>
  Math.max(
    620,
    ...designerBlocks.value.map((item) => item.position.y + 260),
  ),
)
const connectableTargets = computed(() =>
  designerBlocks.value
    .filter((item) => item.id !== selectedBlockId.value)
    .map((item) => ({
      id: item.id,
      label: content.value?.nodes[item.id]?.label || item.id,
    })),
)

function normalizeContent(value: Record<string, unknown>): DesignerContent {
  const normalized = JSON.parse(JSON.stringify(value)) as DesignerContent
  normalized.nodes ??= {}
  normalized.stages ??= []
  normalized.designer ??= { version: 1, blocks: [] }
  normalized.designer.blocks ??= []
  const existing = new Map(
    normalized.designer.blocks.map((block) => [block.id, block]),
  )
  normalized.designer.blocks = Object.entries(normalized.nodes).map(
    ([nodeId, node], index) => {
      const previous = existing.get(nodeId)
      return {
        id: nodeId,
        block_type: previous?.block_type ?? inferBlockType(node),
        position: previous?.position ?? {
          x: 25 + (index % 2) * 210,
          y: 35 + Math.floor(index / 2) * 210,
        },
      }
    },
  )
  return normalized
}

function inferBlockType(node: NodeRule): BlockType {
  if (!node.options.length) return 'end'
  const requirements = node.options.flatMap((option) =>
    option.requirements.map((item) => item.type),
  )
  if (requirements.includes('evidence_ready')) return 'evidence_gate'
  if (requirements.includes('lawyer_assigned')) return 'lawyer_gate'
  if (node.options.length > 1) return 'decision'
  return 'stage'
}

function startPaletteDrag(event: DragEvent, type: BlockType) {
  event.dataTransfer?.setData('application/x-workflow-block-type', type)
  draggingBlockId.value = ''
}

function startBlockDrag(event: DragEvent, blockId: string) {
  draggingBlockId.value = blockId
  event.dataTransfer?.setData('application/x-workflow-block-id', blockId)
}

function dropOnCanvas(event: DragEvent) {
  const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = Math.max(20, event.clientX - bounds.left - 110)
  const y = Math.max(20, event.clientY - bounds.top - 30)
  const type = event.dataTransfer?.getData('application/x-workflow-block-type') as BlockType
  const blockId = event.dataTransfer?.getData('application/x-workflow-block-id')
  if (type) {
    addBlock(type, x, y)
    return
  }
  const block = designerBlocks.value.find(
    (item) => item.id === (blockId || draggingBlockId.value),
  )
  if (block) {
    block.position = { x, y }
    emitContent()
  }
}

function addBlock(type: BlockType, x: number, y: number) {
  if (!content.value) return
  let index = 1
  let id = `${type}-${index}`
  while (content.value.nodes[id]) {
    index += 1
    id = `${type}-${index}`
  }
  const node: NodeRule = {
    stage: content.value.nodes[content.value.start_node]?.stage ?? 'intake',
    label: `${blockTypeLabel(type)} ${index}`,
    options: [],
  }
  content.value.nodes[id] = node
  content.value.designer?.blocks.push({
    id,
    block_type: type,
    position: { x, y },
  })
  selectedBlockId.value = id
  applyBlockType(type)
}

function changeBlockType(type: BlockType) {
  if (!selectedBlock.value) return
  selectedBlock.value.block_type = type
  applyBlockType(type)
}

function applyBlockType(type: BlockType) {
  if (!selectedNode.value) return
  const node = selectedNode.value
  if (type === 'end') {
    node.options = []
    node.stage = 'closed'
  } else if (type === 'stage') {
    node.options = [node.options[0] ?? createOption('顺序出口', 'always')]
    node.options.forEach((option) => {
      option.requirements = [{ type: 'always' }]
    })
  } else if (type === 'decision') {
    while (node.options.length < 2) {
      node.options.push(createOption(`选项 ${node.options.length + 1}`, 'always'))
    }
    node.options.forEach((option) => {
      option.requirements = [{ type: 'always' }]
    })
  } else {
    while (node.options.length < 2) {
      node.options.push(createOption(`出口 ${node.options.length + 1}`, 'always'))
    }
    node.options = node.options.slice(0, 2)
    node.options[0].requirements = [
      {
        type: type === 'evidence_gate' ? 'evidence_ready' : 'lawyer_assigned',
      },
    ]
    node.options[1].requirements = [{ type: 'always' }]
  }
  emitContent()
}

function createOption(label: string, requirement: string): OptionRule {
  optionCounter += 1
  return {
    id: `option-${Date.now()}-${optionCounter}`,
    label,
    description: label,
    target_stage: '',
    target_node: '',
    outcome: '待配置选择后的结果',
    next_step: '待配置下一步操作',
    requirements: [{ type: requirement }],
    deadlines: [],
  }
}

function addOption() {
  if (!selectedNode.value) return
  selectedNode.value.options.push(
    createOption(`选项 ${selectedNode.value.options.length + 1}`, 'always'),
  )
  emitContent()
}

function removeOption(optionId: string) {
  if (!selectedNode.value) return
  selectedNode.value.options = selectedNode.value.options.filter(
    (item) => item.id !== optionId,
  )
  emitContent()
}

function changeTarget(option: OptionRule) {
  if (!content.value || !option.target_node) {
    option.target_stage = ''
  } else {
    option.target_stage = content.value.nodes[option.target_node]?.stage ?? ''
  }
  emitContent()
}

function changeStage() {
  if (!content.value || !selectedNode.value) return
  for (const option of selectedNode.value.options) {
    if (option.target_node) {
      option.target_stage = content.value.nodes[option.target_node]?.stage ?? ''
    }
  }
  emitContent()
}

function removeBlock(blockId: string) {
  if (!content.value || blockId === content.value.start_node) return
  delete content.value.nodes[blockId]
  if (content.value.designer) {
    content.value.designer.blocks = content.value.designer.blocks.filter(
      (item) => item.id !== blockId,
    )
  }
  for (const node of Object.values(content.value.nodes)) {
    for (const option of node.options) {
      if (option.target_node === blockId) {
        option.target_node = ''
        option.target_stage = ''
      }
    }
  }
  selectedBlockId.value = content.value.start_node
  emitContent()
}

function emitContent() {
  if (!content.value) return
  emit('update:modelValue', content.value as unknown as Record<string, unknown>)
}

function blockTypeLabel(type: BlockType) {
  return palette.find((item) => item.type === type)?.label ?? type
}

function stageLabel(stage: string) {
  return content.value?.stages.find((item) => item.key === stage)?.label ?? stage
}
</script>
