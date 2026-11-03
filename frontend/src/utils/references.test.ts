import { describe, expect, it } from 'vitest'

import type { MessageItem } from '../types/api'
import { referencesFromMessage } from './references'

describe('referencesFromMessage', () => {
  it('keeps valid structured references and ignores malformed items', () => {
    const message: MessageItem = {
      id: 1,
      role: 'assistant',
      content: '回答',
      metadata_json: {
        structured: {
          references: [
            {
              type: 'law',
              id: 'cn-labor-50',
              title: '《中华人民共和国劳动法》第五十条',
              excerpt: '工资应当按月支付。',
              source_name: '国家法律法规数据库',
              source_url: 'https://flk.npc.gov.cn/',
              review_status: 'published',
            },
            {
              type: 'unknown',
              id: 'bad',
              title: '无效资料',
              review_status: 'draft',
            },
          ],
        },
      },
      created_at: '2026-11-04T00:00:00Z',
    }

    const result = referencesFromMessage(message)

    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('cn-labor-50')
  })

  it('returns no references for user messages or legacy metadata', () => {
    expect(
      referencesFromMessage({
        id: 2,
        role: 'user',
        content: '问题',
        metadata_json: {},
        created_at: '2026-11-04T00:00:00Z',
      }),
    ).toEqual([])
  })
})
