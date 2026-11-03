import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiFile, apiRequest, apiStream } from './http'

describe('apiFile', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('returns a binary blob for a successful download', async () => {
    localStorage.setItem('lia_token', 'test-token')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(new Blob(['excel-data']), {
        status: 200,
        headers: {
          'Content-Type':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const blob = await apiFile('/admin/rule-packages/template.xlsx')

    expect(blob.size).toBeGreaterThan(0)
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(request.headers).get('Authorization')).toBe(
      'Bearer test-token',
    )
  })

  it('surfaces the server message for an unsuccessful download', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: '无权限' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(
      apiFile('/admin/rule-packages/template.xlsx'),
    ).rejects.toMatchObject({ message: '无权限', status: 403 })
  })

  it('joins structured Excel validation errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              errors: ['路径!F2：目标节点不存在', '阶段!B4：显示名称不能为空'],
            },
          }),
          {
            status: 422,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    )

    await expect(
      apiRequest('/admin/rule-packages/import-excel'),
    ).rejects.toMatchObject({
      message: '路径!F2：目标节点不存在\n阶段!B4：显示名称不能为空',
      status: 422,
    })
  })

  it('consumes authenticated server-sent events', async () => {
    localStorage.setItem('lia_token', 'stream-token')
    const encoder = new TextEncoder()
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode('event: status\ndata: {"stage":"thinking"}\n\n'),
        )
        controller.enqueue(
          encoder.encode('event: delta\ndata: {"text":"工资"}\n\n'),
        )
        controller.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const events: Array<[string, unknown]> = []

    await apiStream('/cases/1/consultations/stream', {}, (event, data) => {
      events.push([event, data])
    })

    expect(events).toEqual([
      ['status', { stage: 'thinking' }],
      ['delta', { text: '工资' }],
    ])
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(request.headers).get('Authorization')).toBe(
      'Bearer stream-token',
    )
  })
})
