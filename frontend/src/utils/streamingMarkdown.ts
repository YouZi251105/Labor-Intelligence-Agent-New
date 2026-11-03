export function stabilizeStreamingMarkdown(content: string): string {
  let stable = content
  const fences = [...stable.matchAll(/```/g)]
  if (fences.length % 2 === 1) {
    const openFence = fences.at(-1)
    const openIndex = openFence?.index ?? stable.length
    const beforeFence = stable.slice(0, openIndex)
    if ((beforeFence.match(/\*\*/g) ?? []).length % 2 === 1) {
      const trimmed = beforeFence.replace(/\s+$/, '')
      const trailing = beforeFence.slice(trimmed.length)
      stable = `${trimmed}**${trailing}${stable.slice(openIndex)}`
    }
    stable += '\n```'
    return stable
  }

  const strongMarkers = (stable.match(/\*\*/g) ?? []).length
  if (strongMarkers % 2 === 1) stable += '**'
  return stable
}
