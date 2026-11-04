export interface WorkflowPoint {
  x: number
  y: number
}

export interface WorkflowRect {
  left: number
  right: number
  top: number
  bottom: number
}

interface WorkflowOptionLike {
  id: string
  label: string
  target_node: string
}

interface WorkflowNodeLike {
  options: WorkflowOptionLike[]
}

export interface WorkflowConnectionContent {
  nodes: Record<string, WorkflowNodeLike>
}

export interface WorkflowConnection {
  id: string
  sourceId: string
  optionId: string
  targetId: string
  label: string
}

export interface WorkflowEdgeGeometry {
  path: string
  targetPoint: WorkflowPoint
  labelX: number
  labelY: number
}

export function collectWorkflowConnections(
  content: WorkflowConnectionContent,
): WorkflowConnection[] {
  const connections: WorkflowConnection[] = []
  for (const [sourceId, node] of Object.entries(content.nodes)) {
    for (const option of node.options) {
      if (!option.target_node || !content.nodes[option.target_node]) continue
      connections.push({
        id: `${sourceId}:${option.id}`,
        sourceId,
        optionId: option.id,
        targetId: option.target_node,
        label: option.label || '未命名出口',
      })
    }
  }
  return connections
}

export function buildWorkflowEdge(input: {
  sourceBlock: WorkflowRect
  sourcePort: WorkflowRect
  targetBlock: WorkflowRect
}): WorkflowEdgeGeometry {
  const { sourceBlock, sourcePort, targetBlock } = input
  const sourceCenter = {
    x: (sourceBlock.left + sourceBlock.right) / 2,
    y: (sourceBlock.top + sourceBlock.bottom) / 2,
  }
  const targetCenter = {
    x: (targetBlock.left + targetBlock.right) / 2,
    y: (targetBlock.top + targetBlock.bottom) / 2,
  }
  const deltaX = targetCenter.x - sourceCenter.x
  const deltaY = targetCenter.y - sourceCenter.y
  const vertical =
    Math.abs(deltaY) > 120 &&
    Math.abs(deltaY) > Math.abs(deltaX) * 0.72
  const sourcePoint = vertical
    ? {
        x: (sourcePort.left + sourcePort.right) / 2,
        y: deltaY >= 0 ? sourcePort.bottom : sourcePort.top,
      }
    : {
        x: deltaX >= 0 ? sourcePort.right : sourcePort.left,
        y: (sourcePort.top + sourcePort.bottom) / 2,
      }
  if (vertical) {
    const targetPoint = {
      x: targetCenter.x,
      y: deltaY >= 0 ? targetBlock.top : targetBlock.bottom,
    }
    const direction = targetPoint.y >= sourcePoint.y ? 1 : -1
    const bend = Math.max(
      52,
      Math.min(180, Math.abs(targetPoint.y - sourcePoint.y) * 0.42),
    )
    const control1 = {
      x: sourcePoint.x,
      y: sourcePoint.y + direction * bend,
    }
    const control2 = {
      x: targetPoint.x,
      y: targetPoint.y - direction * bend,
    }
    return edgeGeometry(sourcePoint, targetPoint, control1, control2)
  }
  const targetCenterX = (targetBlock.left + targetBlock.right) / 2
  const targetOnRight = targetCenterX >= sourcePoint.x
  const targetPoint = {
    x: targetOnRight ? targetBlock.left : targetBlock.right,
    y: targetBlock.top + Math.min(34, (targetBlock.bottom - targetBlock.top) / 2),
  }
  const direction = targetPoint.x >= sourcePoint.x ? 1 : -1
  const bend = Math.max(
    52,
    Math.min(180, Math.abs(targetPoint.x - sourcePoint.x) * 0.48),
  )
  const control1 = {
    x: sourcePoint.x + direction * bend,
    y: sourcePoint.y,
  }
  const control2 = {
    x: targetPoint.x - direction * bend,
    y: targetPoint.y,
  }
  return edgeGeometry(sourcePoint, targetPoint, control1, control2)
}

function edgeGeometry(
  sourcePoint: WorkflowPoint,
  targetPoint: WorkflowPoint,
  control1: WorkflowPoint,
  control2: WorkflowPoint,
): WorkflowEdgeGeometry {
  const labelX =
    (sourcePoint.x +
      3 * control1.x +
      3 * control2.x +
      targetPoint.x) /
    8
  const labelY =
    (sourcePoint.y +
      3 * control1.y +
      3 * control2.y +
      targetPoint.y) /
    8
  return {
    path: [
      `M ${round(sourcePoint.x)} ${round(sourcePoint.y)}`,
      `C ${round(control1.x)} ${round(control1.y)},`,
      `${round(control2.x)} ${round(control2.y)},`,
      `${round(targetPoint.x)} ${round(targetPoint.y)}`,
    ].join(' '),
    targetPoint,
    labelX,
    labelY,
  }
}

function round(value: number) {
  return Math.round(value * 100) / 100
}
