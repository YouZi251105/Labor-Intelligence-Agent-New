import type { FollowUpOption, MessageItem } from '../types/api'

export function followUpOptions(message: MessageItem): FollowUpOption[] {
  if (message.role !== 'assistant') return []
  const structured = message.metadata_json.structured
  if (!structured || typeof structured !== 'object') return []
  const raw = (structured as { follow_up_options?: unknown }).follow_up_options
  if (!Array.isArray(raw)) return []

  return raw
    .flatMap((value) => {
      if (!value || typeof value !== 'object') return []
      const item = value as Partial<FollowUpOption>
      if (
        typeof item.id !== 'string' ||
        !item.id.trim() ||
        typeof item.label !== 'string' ||
        !item.label.trim() ||
        typeof item.message !== 'string' ||
        !item.message.trim() ||
        (item.kind !== 'send' &&
          item.kind !== 'fill' &&
          item.kind !== 'lawyer_request' &&
          item.kind !== 'filing_review')
      ) {
        return []
      }
      return [
        {
          id: item.id.trim(),
          label: item.label.trim(),
          message: item.message.trim(),
          kind: item.kind,
        } satisfies FollowUpOption,
      ]
    })
    .slice(0, 4)
}
