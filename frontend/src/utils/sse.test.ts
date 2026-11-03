import { describe, expect, it, vi } from 'vitest'

import { createSseParser } from './sse'

describe('createSseParser', () => {
  it('parses events split across network chunks', () => {
    const onEvent = vi.fn()
    const parser = createSseParser(onEvent)

    parser.push('event: status\ndata: {"stage":"thinking"}\n')
    parser.push('\n' + 'event: delta\r\ndata: {"text":"工资"}\r\n\r')
    parser.push('\n')
    parser.finish()

    expect(onEvent.mock.calls).toEqual([
      ['status', { stage: 'thinking' }],
      ['delta', { text: '工资' }],
    ])
  })

  it('joins multi-line data and ignores comments', () => {
    const onEvent = vi.fn()
    const parser = createSseParser(onEvent)

    parser.push(': keep-alive\n')
    parser.push('event: error\n')
    parser.push('data: {"detail":"第一行",\n')
    parser.push('data: "code":"E1"}\n\n')
    parser.finish()

    expect(onEvent).toHaveBeenCalledWith('error', {
      detail: '第一行',
      code: 'E1',
    })
  })
})
