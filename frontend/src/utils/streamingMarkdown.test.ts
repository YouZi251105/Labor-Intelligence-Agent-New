import { describe, expect, it } from 'vitest'

import { stabilizeStreamingMarkdown } from './streamingMarkdown'

describe('stabilizeStreamingMarkdown', () => {
  it('closes an unfinished code fence', () => {
    expect(stabilizeStreamingMarkdown('```text\n工资流水')).toBe(
      '```text\n工资流水\n```',
    )
  })

  it('closes an unfinished bold span', () => {
    expect(stabilizeStreamingMarkdown('**有限事实')).toBe('**有限事实**')
  })

  it('leaves complete Markdown unchanged', () => {
    const content = '**重点**\n\n- 工资流水\n- 聊天记录'
    expect(stabilizeStreamingMarkdown(content)).toBe(content)
  })
})
