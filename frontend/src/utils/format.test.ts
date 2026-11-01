import { describe, expect, it } from 'vitest'

import { formatFileSize, getInitial } from './format'

describe('formatFileSize', () => {
  it('formats byte values into readable units', () => {
    expect(formatFileSize(512)).toBe('512 B')
    expect(formatFileSize(1536)).toBe('1.5 KB')
    expect(formatFileSize(5 * 1024 * 1024)).toBe('5.0 MB')
  })

  it('rejects invalid values', () => {
    expect(formatFileSize(-1)).toBe('未知')
    expect(formatFileSize(Number.NaN)).toBe('未知')
  })
})

describe('getInitial', () => {
  it('returns a fallback and trims names', () => {
    expect(getInitial()).toBe('劳')
    expect(getInitial('  zhang ')).toBe('Z')
  })
})
