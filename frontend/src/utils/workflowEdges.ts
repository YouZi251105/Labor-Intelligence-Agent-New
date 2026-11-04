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
  laneOffset?: number
}): WorkflowEdgeGeometry {
  const { sourceBlock, sourcePort, targetBlock, laneOffset = 0 } = input
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
  const vertical = Math.abs(deltaX) < 80 && Math.abs(deltaY) > 80
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
    const laneRange = Math.max(0, Math.abs(targetPoint.y - sourcePoint.y) / 2 - 20)
    const offset = Math.max(-laneRange, Math.min(laneRange, laneOffset))
    const laneY = (sourcePoint.y + targetPoint.y) / 2 + offset
    const path = roundedOrthogonalPath(
      [
        sourcePoint,
        { x: sourcePoint.x, y: laneY },
        { x: targetPoint.x, y: laneY },
        targetPoint,
      ],
      10,
    )
    return {
      path,
      targetPoint,
      labelX: (sourcePoint.x + targetPoint.x) / 2,
      labelY: laneY,
    }
  }
  const targetCenterX = (targetBlock.left + targetBlock.right) / 2
  const targetOnRight = targetCenterX >= sourcePoint.x
  const targetPoint = {
    x: targetOnRight ? targetBlock.left : targetBlock.right,
    y: targetBlock.top + Math.min(34, (targetBlock.bottom - targetBlock.top) / 2),
  }
  const laneRange = Math.max(0, Math.abs(targetPoint.x - sourcePoint.x) / 2 - 20)
  const offset = Math.max(-laneRange, Math.min(laneRange, laneOffset))
  const laneX = (sourcePoint.x + targetPoint.x) / 2 + offset
  const path = roundedOrthogonalPath(
    [
      sourcePoint,
      { x: laneX, y: sourcePoint.y },
      { x: laneX, y: targetPoint.y },
      targetPoint,
    ],
    10,
  )
  return {
    path,
    targetPoint,
    labelX: laneX,
    labelY: (sourcePoint.y + targetPoint.y) / 2,
  }
}

function roundedOrthogonalPath(
  points: WorkflowPoint[],
  radius: number,
): string {
  const compact = points.filter(
    (point, index) =>
      index === 0 ||
      point.x !== points[index - 1].x ||
      point.y !== points[index - 1].y,
  )
  if (compact.length < 2) {
    return `M ${round(compact[0]?.x ?? 0)} ${round(compact[0]?.y ?? 0)}`
  }
  const start = compact[0]
  const commands = [`M ${round(start.x)} ${round(start.y)}`]
  const corners: Array<{
    current: WorkflowPoint
    previous: WorkflowPoint
    next: WorkflowPoint
  }> = []
  for (let index = 1; index < compact.length - 1; index += 1) {
    const previous = compact[index - 1]
    const current = compact[index]
    const next = compact[index + 1]
    if (isCollinear(previous, current, next)) continue
    corners.push({ previous, current, next })
  }
  if (!corners.length) {
    return `${commands[0]} ${axisCommand(start, compact.at(-1)!)}`
  }
  let cursor = start
  for (const { current, next } of corners) {
    const before = moveToward(current, cursor, radius)
    commands.push(axisCommand(cursor, before))
    const after = moveToward(current, next, radius)
    commands.push(
      `Q ${round(current.x)} ${round(current.y)} ${round(after.x)} ${round(after.y)}`,
    )
    cursor = after
  }
  commands.push(axisCommand(cursor, compact.at(-1)!))
  return commands.join(' ')
}

function axisCommand(from: WorkflowPoint, to: WorkflowPoint): string {
  if (from.y === to.y) return `H ${round(to.x)}`
  return `V ${round(to.y)}`
}

function moveToward(
  from: WorkflowPoint,
  to: WorkflowPoint,
  maxDistance: number,
): WorkflowPoint {
  if (from.x === to.x) {
    const distance = Math.sign(to.y - from.y) * Math.min(maxDistance, Math.abs(to.y - from.y) / 2)
    return { x: from.x, y: from.y + distance }
  }
  const distance = Math.sign(to.x - from.x) * Math.min(maxDistance, Math.abs(to.x - from.x) / 2)
  return { x: from.x + distance, y: from.y }
}

function isCollinear(
  previous: WorkflowPoint,
  current: WorkflowPoint,
  next: WorkflowPoint,
): boolean {
  return (
    (previous.x === current.x && current.x === next.x) ||
    (previous.y === current.y && current.y === next.y)
  )
}

function round(value: number) {
  return Math.round(value * 100) / 100
}
