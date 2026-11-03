import { describe, expect, it } from 'vitest'

import type { MessageItem } from '../types/api'
import { followUpOptions } from './followUps'

function assistantMessage(options: unknown): MessageItem {
  return {
    id: 1,
    role: 'assistant',
    content: '建议先整理材料。',
    metadata_json: {
      structured: {
        follow_up_options: options,
      },
    },
    created_at: '2026-11-03T10:00:00Z',
  }
}

describe('followUpOptions', () => {
  it('normalizes persisted follow-up options for an assistant message', () => {
    const result = followUpOptions(
      assistantMessage([
        {
          id: 'missing-wage',
          label: '补充工资标准',
          message: '关于工资标准，我的情况是：',
          kind: 'fill',
        },
        {
          id: 'next-step',
          label: '协商还是仲裁',
          message: '根据我的情况，下一步应该协商还是申请仲裁？',
          kind: 'send',
        },
      ]),
    )

    expect(result).toHaveLength(2)
    expect(result[0].kind).toBe('fill')
  })

  it('ignores invalid options and limits the list to four entries', () => {
    const result = followUpOptions(
      assistantMessage([
        ...Array.from({ length: 5 }, (_, index) => ({
          id: `item-${index}`,
          label: `问题 ${index}`,
          message: `消息 ${index}`,
          kind: 'send',
        })),
        { id: 'invalid', label: '', message: '消息', kind: 'send' },
        { id: 'invalid-kind', label: '无效', message: '消息', kind: 'other' },
      ]),
    )

    expect(result).toHaveLength(4)
  })
})
