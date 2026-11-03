import type { MessageItem, ReferenceItem } from '../types/api'

export function referencesFromMessage(message: MessageItem): ReferenceItem[] {
  if (message.role !== 'assistant') return []
  const structured = message.metadata_json.structured
  if (!structured || typeof structured !== 'object') return []
  const raw = (structured as { references?: unknown }).references
  if (!Array.isArray(raw)) return []

  return raw.filter((item): item is ReferenceItem => {
    if (!item || typeof item !== 'object') return false
    const reference = item as Partial<ReferenceItem>
    return (
      (reference.type === 'law' || reference.type === 'case') &&
      typeof reference.id === 'string' &&
      typeof reference.title === 'string' &&
      typeof reference.review_status === 'string'
    )
  })
}
