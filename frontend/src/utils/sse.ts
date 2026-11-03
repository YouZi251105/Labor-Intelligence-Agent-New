export interface SseParser {
  push: (chunk: string) => void
  finish: () => void
}

export function createSseParser(
  onEvent: (event: string, data: unknown) => void,
): SseParser {
  let buffer = ''

  function parseBlock(block: string): void {
    const dataLines: string[] = []
    let event = 'message'
    for (const line of block.split(/\r?\n/)) {
      if (!line || line.startsWith(':')) continue
      if (line.startsWith('event:')) {
        event = line.slice('event:'.length).trim() || 'message'
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trimStart())
      }
    }
    if (!dataLines.length) return
    const payload = dataLines.join('\n')
    try {
      onEvent(event, JSON.parse(payload))
    } catch (error) {
      throw new Error(
        `无法解析服务端流事件：${error instanceof Error ? error.message : String(error)}`,
      )
    }
  }

  function drain(): void {
    while (true) {
      const match = /\r?\n\r?\n/.exec(buffer)
      if (!match || match.index === undefined) return
      const block = buffer.slice(0, match.index)
      buffer = buffer.slice(match.index + match[0].length)
      parseBlock(block)
    }
  }

  return {
    push(chunk: string) {
      buffer += chunk
      drain()
    },
    finish() {
      if (buffer.trim()) parseBlock(buffer)
      buffer = ''
    },
  }
}
