import { describe, expect, it } from 'vitest'

import type { MessageItem } from '../types/api'
import {
  activeFollowUpOptions,
  followUpOptions,
  latestActionableAssistantMessageId,
} from './followUps'

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

  it('preserves lawyer and filing review action options', () => {
    const result = followUpOptions(
      assistantMessage([
        {
          id: 'lawyer',
          label: '预约律师',
          message: '申请律师介入',
          kind: 'lawyer_request',
        },
        {
          id: 'review',
          label: '申请立案前复核',
          message: '申请正式流程前复核',
          kind: 'filing_review',
        },
      ]),
    )

    expect(result.map((item) => item.kind)).toEqual([
      'lawyer_request',
      'filing_review',
    ])
  })
})

describe('activeFollowUpOptions', () => {
  it('only exposes options for a trailing assistant message', () => {
    const assistant = assistantMessage([
      {
        id: 'next-step',
        label: '下一步怎么走',
        message: '下一步应该怎么做？',
        kind: 'send',
      },
    ])
    const userMessage: MessageItem = {
      ...assistant,
      id: 2,
      role: 'user',
      content: '补充事实',
    }

    expect(latestActionableAssistantMessageId([assistant])).toBe(1)
    expect(latestActionableAssistantMessageId([assistant, userMessage])).toBeNull()
  })

  it('hides options already consumed by the user', () => {
    const message = assistantMessage([
      {
        id: 'lawyer',
        label: '申请律师协助',
        message: '申请律师介入',
        kind: 'lawyer_request',
      },
      {
        id: 'materials',
        label: '检查材料',
        message: '请帮我检查材料。',
        kind: 'send',
      },
    ])

    const result = activeFollowUpOptions(message, message.id, new Set(['1:lawyer']))

    expect(result.map((item) => item.id)).toEqual(['materials'])
  })
})
