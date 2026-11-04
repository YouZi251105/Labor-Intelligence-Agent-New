<template>
  <div
    v-if="content"
    class="workflow-designer"
    :class="{ 'workflow-designer--readonly': readonly }"
  >
    <aside v-if="!readonly" class="workflow-designer__palette">
      <div class="workflow-designer__palette-heading">
        <div>
          <span class="eyebrow">受控积木</span>
          <h3>流程组件</h3>
        </div>
        <button
          type="button"
          class="workflow-auto-layout"
          title="自动整理画布"
          aria-label="自动整理"
          @click="autoArrangeBlocks"
        >
          <LayoutGrid :size="15" />
        </button>
      </div>
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
        点击添加积木；桌面端也可拖入画布。选中后可微调位置，出口目标决定连线方向。
      </p>
    </aside>

    <section
      ref="canvasRef"
      class="workflow-designer__canvas"
    >
      <div
        ref="stageRef"
        class="workflow-designer__stage"
        :style="{ width: `${stageWidth}px`, height: `${canvasHeight}px` }"
        @dragover.prevent
        @drop="dropOnCanvas"
      >
        <svg
          v-if="workflowEdges.length"
          class="workflow-connections"
          :width="stageWidth"
          :height="canvasHeight"
          aria-label="流程图连线"
        >
          <defs>
            <marker
              id="workflow-arrowhead"
              markerWidth="9"
              markerHeight="9"
              refX="7"
              refY="4.5"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M 0 0 L 9 4.5 L 0 9 z" fill="currentColor" />
            </marker>
          </defs>
          <g
            v-for="edge in workflowEdges"
            :key="edge.id"
            class="workflow-connection"
            :class="{ active: edge.active }"
            :data-edge-id="edge.id"
          >
            <path
              class="workflow-connection__path"
              :d="edge.path"
              marker-end="url(#workflow-arrowhead)"
            />
            <path
              class="workflow-connection__hit"
              :d="edge.path"
              @click.stop="selectConnection(edge.sourceId)"
            />
            <g
              class="workflow-connection__label"
              :transform="`translate(${edge.labelX} ${edge.labelY})`"
            >
              <rect
                :x="-edge.labelWidth / 2"
                y="-11"
                :width="edge.labelWidth"
                height="22"
                rx="6"
              />
              <text text-anchor="middle" dy="3.5">{{ edge.label }}</text>
            </g>
          </g>
        </svg>

        <article
          v-for="block in designerBlocks"
          :key="block.id"
          :ref="(element) => setBlockElement(block.id, element as HTMLElement | null)"
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
            :draggable="!readonly"
            @dragstart="startBlockDrag($event, block.id)"
          >
            <span class="workflow-block__kind">{{ blockTypeLabel(block.block_type) }}</span>
            <strong>{{ content.nodes[block.id]?.label || block.id }}</strong>
            <small>{{ block.id }} · {{ stageLabel(content.nodes[block.id]?.stage ?? '') }}</small>
          </header>
          <div class="workflow-block__ports">
            <div
              v-for="option in content.nodes[block.id]?.options ?? []"
              :key="option.id"
              :ref="
                (element) =>
                  setPortElement(
                    block.id,
                    option.id,
                    element as HTMLElement | null,
                  )
              "
            >
              <span>{{ option.label || '未命名出口' }}</span>
              <strong>{{ option.target_node || '未连接' }}</strong>
            </div>
            <small v-if="block.block_type === 'end'">流程结束，无输出</small>
          </div>
        </article>
        <p v-if="!designerBlocks.length" class="workflow-designer__empty">
          从左侧添加第一个流程积木。
        </p>
      </div>
    </section>

    <aside v-if="selectedBlock && selectedNode" class="workflow-designer__inspector">
      <div class="workflow-designer__inspector-heading">
        <div>
          <span class="eyebrow">{{ readonly ? '积木详情' : '积木设置' }}</span>
          <h3>{{ selectedNode.label || selectedBlock.id }}</h3>
        </div>
        <button
          v-if="!readonly"
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
        <input v-model="selectedNode.label" :disabled="readonly" @input="emitContent" />
      </label>
      <label>
        <span>业务阶段</span>
        <select v-model="selectedNode.stage" :disabled="readonly" @change="changeStage">
          <option v-for="stage in content.stages" :key="stage.key" :value="stage.key">
            {{ stage.label }}
          </option>
        </select>
      </label>
      <label>
        <span>积木类型</span>
        <select
          :disabled="readonly"
          :value="selectedBlock.block_type"
          @change="changeBlockType(($event.target as HTMLSelectElement).value as BlockType)"
        >
          <option v-for="item in palette" :key="item.type" :value="item.type">
            {{ item.label }}
          </option>
        </select>
      </label>

      <div v-if="!readonly" class="workflow-position-controls">
        <span>位置微调</span>
        <div class="workflow-position-controls__grid">
          <button
            type="button"
            title="上移积木"
            aria-label="上移积木"
            @click="nudgeSelected(0, -32)"
          >
            <ArrowUp :size="16" />
          </button>
          <button
            type="button"
            title="左移积木"
            aria-label="左移积木"
            @click="nudgeSelected(-32, 0)"
          >
            <ArrowLeft :size="16" />
          </button>
          <button
            type="button"
            title="自动整理"
            aria-label="自动整理"
            @click="autoArrangeBlocks"
          >
            <LayoutGrid :size="16" />
          </button>
          <button
            type="button"
            title="右移积木"
            aria-label="右移积木"
            @click="nudgeSelected(32, 0)"
          >
            <ArrowRight :size="16" />
          </button>
          <button
            type="button"
            title="下移积木"
            aria-label="下移积木"
            @click="nudgeSelected(0, 32)"
          >
            <ArrowDown :size="16" />
          </button>
        </div>
      </div>

      <div v-if="selectedBlock.block_type !== 'end'" class="workflow-outlets">
        <div class="workflow-outlets__heading">
          <strong>出口与去向</strong>
          <button
            v-if="!readonly && selectedBlock.block_type === 'decision'"
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
            <input v-model="option.label" :disabled="readonly" @input="emitContent" />
          </label>
          <label>
            <span>目标积木</span>
            <select
              v-model="option.target_node"
              :disabled="readonly"
              @change="changeTarget(option)"
            >
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
            <textarea
              v-model="option.outcome"
              rows="2"
              :disabled="readonly"
              @input="emitContent"
            />
          </label>
          <label>
            <span>下一步操作</span>
            <textarea
              v-model="option.next_step"
              rows="2"
              :disabled="readonly"
              @input="emitContent"
            />
          </label>
          <button
            v-if="
              !readonly &&
              selectedBlock.block_type === 'decision' &&
              selectedNode.options.length > 2
            "
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
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  CircleStop,
  FileCheck2,
  GitBranch,
  LayoutGrid,
  Plus,
  Scale,
  ShieldCheck,
  Trash2,
} from '@lucide/vue'
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'

import {
  buildWorkflowEdge,
  collectWorkflowConnections,
  type WorkflowConnection,
  type WorkflowEdgeGeometry,
  type WorkflowRect,
} from '../utils/workflowEdges'

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
    blocks: BlockRule[] | Record<string, BlockRule>
  }
}

interface MeasuredBlock extends WorkflowRect {
  width: number
  height: number
}

interface RenderedWorkflowEdge
  extends WorkflowConnection,
    WorkflowEdgeGeometry {
  active: boolean
  labelWidth: number
}

const props = defineProps<{
  modelValue: Record<string, unknown>
  readonly?: boolean
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
const canvasRef = ref<HTMLElement | null>(null)
const stageRef = ref<HTMLElement | null>(null)
const measuredBlocks = ref<Record<string, MeasuredBlock>>({})
const measuredPorts = ref<Record<string, WorkflowRect>>({})
const viewportWidth = ref(720)
const blockElements = new Map<string, HTMLElement>()
const portElements = new Map<string, HTMLElement>()
let optionCounter = 0
let measureFrame = 0
let resizeObserver: ResizeObserver | null = null
const readonly = computed(() => Boolean(props.readonly))

watch(
  () => props.modelValue,
  (value) => {
    content.value = normalizeContent(value)
    if (!props.readonly && JSON.stringify(content.value) !== JSON.stringify(value)) {
      emit('update:modelValue', content.value as unknown as Record<string, unknown>)
    }
    if (!selectedBlockId.value || !content.value.nodes[selectedBlockId.value]) {
      selectedBlockId.value = content.value.start_node
    }
  },
  { immediate: true, deep: true },
)

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(scheduleMeasure)
  }
  if (canvasRef.value) resizeObserver?.observe(canvasRef.value)
  for (const element of blockElements.values()) {
    resizeObserver?.observe(element)
  }
  for (const element of portElements.values()) {
    resizeObserver?.observe(element)
  }
  scheduleMeasure()
})

onBeforeUnmount(() => {
  if (measureFrame) cancelAnimationFrame(measureFrame)
  resizeObserver?.disconnect()
  resizeObserver = null
  blockElements.clear()
  portElements.clear()
})

const designerBlocks = computed<BlockRule[]>(() => {
  const blocks = content.value?.designer?.blocks
  if (!blocks) return []
  return Array.isArray(blocks) ? blocks : Object.values(blocks)
})
const selectedBlock = computed(() =>
  designerBlocks.value.find((item) => item.id === selectedBlockId.value),
)
const selectedNode = computed(() =>
  selectedBlock.value && content.value
    ? content.value.nodes[selectedBlock.value.id]
    : null,
)
const nextAutoY = computed(() => {
  const bottom = Math.max(
    0,
    ...designerBlocks.value.map((item) => {
      const measured = measuredBlocks.value[item.id]
      return item.position.y + (measured?.height ?? 170)
    }),
  )
  return bottom + 48
})
const canvasHeight = computed(() =>
  Math.max(
    620,
    ...designerBlocks.value.map((item) => {
      const measured = measuredBlocks.value[item.id]
      return item.position.y + (measured?.height ?? 190) + 80
    }),
  ),
)
const stageWidth = computed(() =>
  Math.max(
    720,
    viewportWidth.value,
    ...designerBlocks.value.map((item) => {
      const measured = measuredBlocks.value[item.id]
      return item.position.x + (measured?.width ?? 200) + 90
    }),
  ),
)
const workflowConnections = computed(() =>
  content.value
    ? collectWorkflowConnections(content.value)
    : [],
)
const workflowEdges = computed<RenderedWorkflowEdge[]>(() => {
  const edges: RenderedWorkflowEdge[] = []
  for (const connection of workflowConnections.value) {
    const sourceBlock = measuredBlocks.value[connection.sourceId]
    const targetBlock = measuredBlocks.value[connection.targetId]
    const port = measuredPorts.value[`${connection.sourceId}:${connection.optionId}`]
    if (!sourceBlock || !targetBlock || !port) continue
    const geometry = buildWorkflowEdge({
      sourceBlock,
      sourcePort: port,
      targetBlock,
    })
    edges.push({
      ...connection,
      ...geometry,
      active:
        selectedBlockId.value === connection.sourceId ||
        selectedBlockId.value === connection.targetId,
      labelWidth: Math.max(
        54,
        Math.min(150, connection.label.length * 13 + 20),
      ),
    })
  }
  return edges
})
const connectableTargets = computed(() =>
  designerBlocks.value
    .filter((item) => item.id !== selectedBlockId.value)
    .map((item) => ({
      id: item.id,
      label: content.value?.nodes[item.id]?.label || item.id,
    })),
)

function setBlockElement(blockId: string, element: HTMLElement | null) {
  const current = blockElements.get(blockId)
  if (current === element) return
  if (current) resizeObserver?.unobserve(current)
  if (element) {
    blockElements.set(blockId, element)
    resizeObserver?.observe(element)
  } else {
    blockElements.delete(blockId)
  }
  scheduleMeasure()
}

function setPortElement(
  blockId: string,
  optionId: string,
  element: HTMLElement | null,
) {
  const key = `${blockId}:${optionId}`
  const current = portElements.get(key)
  if (current === element) return
  if (current) resizeObserver?.unobserve(current)
  if (element) {
    portElements.set(key, element)
    resizeObserver?.observe(element)
  } else {
    portElements.delete(key)
  }
  scheduleMeasure()
}

function scheduleMeasure() {
  if (measureFrame) return
  measureFrame = window.requestAnimationFrame(() => {
    measureFrame = 0
    measureCanvas()
  })
}

function measureCanvas() {
  const canvas = canvasRef.value
  const stage = stageRef.value
  if (!canvas || !stage) return
  viewportWidth.value = canvas.clientWidth || 720
  const stageRect = stage.getBoundingClientRect()
  const nextBlocks: Record<string, MeasuredBlock> = {}
  for (const [blockId, element] of blockElements) {
    const rect = element.getBoundingClientRect()
    if (!rect.width || !rect.height) continue
    nextBlocks[blockId] = {
      left: rect.left - stageRect.left,
      right: rect.right - stageRect.left,
      top: rect.top - stageRect.top,
      bottom: rect.bottom - stageRect.top,
      width: rect.width,
      height: rect.height,
    }
  }
  const nextPorts: Record<string, WorkflowRect> = {}
  for (const [key, element] of portElements) {
    const rect = element.getBoundingClientRect()
    if (!rect.width || !rect.height) continue
    nextPorts[key] = {
      left: rect.left - stageRect.left,
      right: rect.right - stageRect.left,
      top: rect.top - stageRect.top,
      bottom: rect.bottom - stageRect.top,
    }
  }
  measuredBlocks.value = nextBlocks
  measuredPorts.value = nextPorts
}

function selectConnection(sourceId: string) {
  selectedBlockId.value = sourceId
}

function normalizeContent(value: Record<string, unknown>): DesignerContent {
  const normalized = JSON.parse(JSON.stringify(value)) as DesignerContent
  normalized.nodes ??= {}
  normalized.stages ??= []
  normalized.designer ??= { version: 1, blocks: [] }
  normalized.designer.blocks ??= []
  const blockValues = Array.isArray(normalized.designer.blocks)
    ? normalized.designer.blocks
    : Object.values(normalized.designer.blocks)
  const existing = new Map(
    blockValues.map((block) => [block.id, block]),
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
  if (readonly.value) return
  event.dataTransfer?.setData('application/x-workflow-block-type', type)
  draggingBlockId.value = ''
}

function startBlockDrag(event: DragEvent, blockId: string) {
  if (readonly.value) return
  draggingBlockId.value = blockId
  event.dataTransfer?.setData('application/x-workflow-block-id', blockId)
}

function dropOnCanvas(event: DragEvent) {
  if (readonly.value) return
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

function nudgeSelected(deltaX: number, deltaY: number) {
  if (readonly.value || !selectedBlock.value) return
  selectedBlock.value.position = {
    x: Math.max(16, selectedBlock.value.position.x + deltaX),
    y: Math.max(16, selectedBlock.value.position.y + deltaY),
  }
  emitContent()
}

function autoArrangeBlocks() {
  if (readonly.value || !content.value || !designerBlocks.value.length) return
  const depths = new Map<string, number>()
  const queue: string[] = []
  if (content.value.nodes[content.value.start_node]) {
    depths.set(content.value.start_node, 0)
    queue.push(content.value.start_node)
  }
  while (queue.length) {
    const nodeId = queue.shift()
    if (!nodeId) continue
    const depth = depths.get(nodeId) ?? 0
    for (const option of content.value.nodes[nodeId]?.options ?? []) {
      if (!content.value.nodes[option.target_node]) continue
      if (depths.has(option.target_node)) continue
      depths.set(option.target_node, depth + 1)
      queue.push(option.target_node)
    }
  }
  const remainingDepth =
    Math.max(0, ...Array.from(depths.values())) + 1
  for (const block of designerBlocks.value) {
    if (!depths.has(block.id)) depths.set(block.id, remainingDepth)
  }
  const groups = new Map<number, BlockRule[]>()
  for (const block of designerBlocks.value) {
    const depth = depths.get(block.id) ?? 0
    const group = groups.get(depth) ?? []
    group.push(block)
    groups.set(depth, group)
  }
  for (const [depth, blocks] of [...groups.entries()].sort(
    ([left], [right]) => left - right,
  )) {
    blocks.forEach((block, index) => {
      block.position = {
        x: 32 + depth * 270,
        y: 42 + index * 210,
      }
    })
  }
  emitContent()
}

function addBlock(type: BlockType, x: number, y: number) {
  if (readonly.value) return
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
  mutableBlocks().push({
    id,
    block_type: type,
    position: { x, y },
  })
  selectedBlockId.value = id
  applyBlockType(type)
}

function changeBlockType(type: BlockType) {
  if (readonly.value) return
  if (!selectedBlock.value) return
  selectedBlock.value.block_type = type
  applyBlockType(type)
}

function applyBlockType(type: BlockType) {
  if (readonly.value) return
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
  if (readonly.value) return
  if (!selectedNode.value) return
  selectedNode.value.options.push(
    createOption(`选项 ${selectedNode.value.options.length + 1}`, 'always'),
  )
  emitContent()
}

function removeOption(optionId: string) {
  if (readonly.value) return
  if (!selectedNode.value) return
  selectedNode.value.options = selectedNode.value.options.filter(
    (item) => item.id !== optionId,
  )
  emitContent()
}

function changeTarget(option: OptionRule) {
  if (readonly.value) return
  if (!content.value || !option.target_node) {
    option.target_stage = ''
  } else {
    option.target_stage = content.value.nodes[option.target_node]?.stage ?? ''
  }
  emitContent()
}

function changeStage() {
  if (readonly.value) return
  if (!content.value || !selectedNode.value) return
  for (const option of selectedNode.value.options) {
    if (option.target_node) {
      option.target_stage = content.value.nodes[option.target_node]?.stage ?? ''
    }
  }
  emitContent()
}

function removeBlock(blockId: string) {
  if (readonly.value) return
  if (!content.value || blockId === content.value.start_node) return
  delete content.value.nodes[blockId]
  if (content.value.designer) {
    content.value.designer.blocks = mutableBlocks().filter(
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
  if (readonly.value) return
  if (!content.value) return
  emit('update:modelValue', content.value as unknown as Record<string, unknown>)
  void nextTick(scheduleMeasure)
}

function blockTypeLabel(type: BlockType) {
  return palette.find((item) => item.type === type)?.label ?? type
}

function stageLabel(stage: string) {
  return content.value?.stages.find((item) => item.key === stage)?.label ?? stage
}

function mutableBlocks(): BlockRule[] {
  if (!content.value?.designer) return []
  if (!Array.isArray(content.value.designer.blocks)) {
    content.value.designer.blocks = Object.values(content.value.designer.blocks)
  }
  return content.value.designer.blocks
}
</script>
