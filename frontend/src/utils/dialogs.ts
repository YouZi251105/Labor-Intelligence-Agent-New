import { ElMessage, ElMessageBox } from 'element-plus'

interface ConfirmOptions {
  title?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

export async function confirmAction(
  message: string,
  options: ConfirmOptions = {},
): Promise<boolean> {
  const {
    title = '请确认',
    confirmText = '确认',
    cancelText = '取消',
    danger = false,
  } = options
  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
      confirmButtonClass: danger ? 'lia-confirm-dialog__danger' : undefined,
      type: 'warning',
      customClass: 'lia-confirm-dialog',
      closeOnClickModal: false,
      distinguishCancelAndClose: true,
    })
    return true
  } catch {
    return false
  }
}

export async function promptForPassword(message: string): Promise<string | null> {
  try {
    const result = await ElMessageBox.prompt(message, '重置密码', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'password',
      inputPlaceholder: '请输入至少 8 位新密码',
      inputValidator: (value: string) =>
        value.trim().length >= 8 || '密码至少 8 位',
      customClass: 'lia-confirm-dialog',
      closeOnClickModal: false,
    })
    return result.value?.trim() || null
  } catch {
    return null
  }
}

interface PromptTextOptions {
  title?: string
  placeholder?: string
  required?: boolean
  requiredMessage?: string
  multiline?: boolean
}

export async function promptForText(
  message: string,
  options: PromptTextOptions = {},
): Promise<string | null> {
  const {
    title = '请填写',
    placeholder = '',
    required = true,
    requiredMessage = '内容不能为空',
    multiline = false,
  } = options
  try {
    const result = await ElMessageBox.prompt(message, title, {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: multiline ? 'textarea' : 'text',
      inputPlaceholder: placeholder,
      inputValidator: (value: string) =>
        !required || value.trim().length > 0 || requiredMessage,
      customClass: 'lia-confirm-dialog',
      closeOnClickModal: false,
    })
    return result.value?.trim() || null
  } catch {
    return null
  }
}

export function notifySuccess(message: string): void {
  ElMessage.success(message)
}
