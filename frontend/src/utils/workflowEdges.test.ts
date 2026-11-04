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
  it('connects rightward with a cubic path and centered label', () => {
    const edge = buildWorkflowEdge({
      sourceBlock: { left: 20, right: 220, top: 40, bottom: 180 },
      sourcePort: { left: 30, right: 210, top: 90, bottom: 118 },
      targetBlock: { left: 360, right: 560, top: 70, bottom: 210 },
    })

    expect(edge.path).toContain('M 210 104')
    expect(edge.path).toContain('C ')
    expect(edge.targetPoint.x).toBe(360)
    expect(edge.labelX).toBeGreaterThan(220)
    expect(edge.labelX).toBeLessThan(360)
  })

  it('leaves a leftward source from its left port', () => {
    const edge = buildWorkflowEdge({
      sourceBlock: { left: 220, right: 420, top: 40, bottom: 180 },
      sourcePort: { left: 230, right: 410, top: 90, bottom: 118 },
      targetBlock: { left: -180, right: 20, top: 260, bottom: 400 },
    })

    expect(edge.targetPoint.x).toBe(20)
    expect(edge.path).toContain('C ')
    expect(edge.labelY).toBeGreaterThan(104)
  })

  it('uses bottom and top anchors for a vertical path in the same column', () => {
    const edge = buildWorkflowEdge({
      sourceBlock: { left: 20, right: 220, top: 40, bottom: 180 },
      sourcePort: { left: 30, right: 210, top: 90, bottom: 118 },
      targetBlock: { left: 20, right: 220, top: 300, bottom: 440 },
    })

    expect(edge.path).toContain('M 120 118')
    expect(edge.targetPoint).toEqual({ x: 120, y: 300 })
    expect(edge.labelY).toBeGreaterThan(118)
    expect(edge.labelY).toBeLessThan(300)
  })
})
