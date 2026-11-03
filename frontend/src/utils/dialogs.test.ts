import { beforeEach, describe, expect, it, vi } from 'vitest'

const { confirmMock, promptMock, successMock } = vi.hoisted(() => ({
  confirmMock: vi.fn(),
  promptMock: vi.fn(),
  successMock: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: successMock },
  ElMessageBox: {
    confirm: confirmMock,
    prompt: promptMock,
  },
}))

import { confirmAction, notifySuccess, promptForPassword } from './dialogs'

describe('dialogs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns true after an in-app confirmation', async () => {
    confirmMock.mockResolvedValue('confirm')

    await expect(
      confirmAction('确定删除该案件？', {
        title: '删除案件',
        confirmText: '删除',
        danger: true,
      }),
    ).resolves.toBe(true)
    expect(confirmMock).toHaveBeenCalledWith(
      '确定删除该案件？',
      '删除案件',
      expect.objectContaining({
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        customClass: 'lia-confirm-dialog',
      }),
    )
  })

  it('returns false when an in-app confirmation is cancelled', async () => {
    confirmMock.mockRejectedValue('cancel')

    await expect(confirmAction('继续吗？')).resolves.toBe(false)
  })

  it('uses an in-app password prompt and returns its value', async () => {
    promptMock.mockResolvedValue({ value: 'NewPassword123!' })

    await expect(
      promptForPassword('为 admin 设置新密码'),
    ).resolves.toBe('NewPassword123!')
    expect(promptMock).toHaveBeenCalledWith(
      '为 admin 设置新密码',
      '重置密码',
      expect.objectContaining({
        inputType: 'password',
        inputValidator: expect.any(Function),
        customClass: 'lia-confirm-dialog',
      }),
    )
  })

  it('uses the system success message component', () => {
    notifySuccess('已删除')

    expect(successMock).toHaveBeenCalledWith('已删除')
  })
})
