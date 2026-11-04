import { describe, expect, it } from 'vitest'

import {
  buildWorkflowEdge,
  collectWorkflowConnections,
} from './workflowEdges'

describe('collectWorkflowConnections', () => {
  it('only returns options with an existing target node', () => {
    const connections = collectWorkflowConnections({
      nodes: {
        start: {
          options: [
            { id: 'ready', label: '材料齐全', target_node: 'review' },
            { id: 'missing', label: '仍需补充', target_node: '' },
            { id: 'broken', label: '失效路径', target_node: 'removed' },
          ],
        },
        review: {
          options: [],
        },
      },
    })

    expect(connections).toEqual([
      {
        id: 'start:ready',
        sourceId: 'start',
        optionId: 'ready',
        targetId: 'review',
        label: '材料齐全',
      },
    ])
  })
})

describe('buildWorkflowEdge', () => {
  it('connects rightward through the gap with an orthogonal path', () => {
    const edge = buildWorkflowEdge({
      sourceBlock: { left: 20, right: 220, top: 40, bottom: 180 },
      sourcePort: { left: 30, right: 210, top: 90, bottom: 118 },
      targetBlock: { left: 360, right: 560, top: 150, bottom: 290 },
      laneOffset: 0,
    })

    expect(edge.path).toContain('M 210 104')
    expect(edge.path).toContain('H ')
    expect(edge.path).toContain('V ')
    expect(edge.path).toContain('Q ')
    expect(edge.path).not.toContain('C ')
    expect(edge.targetPoint.x).toBe(360)
    expect(edge.labelX).toBeGreaterThan(220)
    expect(edge.labelX).toBeLessThan(360)
  })

  it('leaves a leftward source from its left port', () => {
    const edge = buildWorkflowEdge({
      sourceBlock: { left: 220, right: 420, top: 40, bottom: 180 },
      sourcePort: { left: 230, right: 410, top: 90, bottom: 118 },
      targetBlock: { left: -180, right: 20, top: 260, bottom: 400 },
      laneOffset: 0,
    })

    expect(edge.targetPoint.x).toBe(20)
    expect(edge.path).toContain('H ')
    expect(edge.path).toContain('V ')
    expect(edge.path).not.toContain('C ')
    expect(edge.labelY).toBeGreaterThan(104)
  })

  it('uses a horizontal lane for a vertical path in the same column', () => {
    const edge = buildWorkflowEdge({
      sourceBlock: { left: 20, right: 220, top: 40, bottom: 180 },
      sourcePort: { left: 30, right: 210, top: 90, bottom: 118 },
      targetBlock: { left: 20, right: 220, top: 300, bottom: 440 },
      laneOffset: 0,
    })

    expect(edge.path).toContain('M 120 118')
    expect(edge.targetPoint).toEqual({ x: 120, y: 300 })
    expect(edge.path).toContain('V ')
    expect(edge.path).not.toContain('C ')
    expect(edge.labelY).toBeGreaterThan(118)
    expect(edge.labelY).toBeLessThan(300)
  })

  it('separates shared lanes with a deterministic offset', () => {
    const input = {
      sourceBlock: { left: 20, right: 220, top: 40, bottom: 180 },
      sourcePort: { left: 30, right: 210, top: 90, bottom: 118 },
      targetBlock: { left: 360, right: 560, top: 240, bottom: 380 },
    }

    const center = buildWorkflowEdge({ ...input, laneOffset: 0 })
    const shifted = buildWorkflowEdge({ ...input, laneOffset: 12 })

    expect(center.labelX).not.toBe(shifted.labelX)
    expect(shifted.labelX).toBeGreaterThan(center.labelX)
  })
})
