import { expect, type Page, test } from '@playwright/test'

async function login(page: Page, username: string, password: string) {
  await page.goto('/login')
  await page.getByRole('textbox').first().fill(username)
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
}

test('login page is accessible', async ({ page }, testInfo) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath(`login-${testInfo.project.name}.png`),
    fullPage: true,
  })
})

test('worker can consult, review a contract, and generate a document', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  await expect(page.getByRole('heading', { name: '工地欠薪咨询' })).toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath(`workspace-${testInfo.project.name}.png`),
    fullPage: true,
  })

  await page.goto('/cases')
  await expect(page.getByRole('heading', { name: '我的案件' })).toBeVisible()
  await page.locator('.case-card').first().click()

  await page.getByRole('button', { name: '咨询记录' }).click()
  await page.locator('.chat-compose-inline textarea').fill('老板说这周还是不能发工资，我还需要准备什么？')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(
    page.locator('.chat-message--assistant p').filter({ hasText: '本地演示规则回复' }).last(),
  ).toBeVisible()

  await page.getByRole('button', { name: '证据材料' }).click()
  const evidenceName = `聊天记录-${testInfo.project.name}.txt`
  await page.locator('input[type="file"]').setInputFiles({
    name: evidenceName,
    mimeType: 'text/plain',
    buffer: Buffer.from(
      `老板：这个月工资下周再发。劳动者：已经拖了两个月。测试视口：${testInfo.project.name}`,
    ),
  })
  await expect(page.getByText(evidenceName)).toBeVisible()

  await page.getByRole('button', { name: '合同审查' }).click()
  await page.locator('.large-textarea').fill(
    '甲方可以随时解除合同，乙方自愿放弃社会保险，工资另行约定。',
  )
  await page.getByRole('button', { name: '开始审查' }).click()
  await expect(page.getByText('风险等级：高')).toBeVisible()

  await page.getByRole('button', { name: '法律文书' }).click()
  await page.getByRole('button', { name: '劳动仲裁申请书' }).click()
  await expect(page.locator('.document-preview')).toContainText('劳动仲裁申请书')

  await page.screenshot({
    path: testInfo.outputPath(`case-workspace-${testInfo.project.name}.png`),
    fullPage: true,
  })
})

test('admin can open the management dashboard', async ({ page }, testInfo) => {
  await login(page, 'admin', 'Admin123!')
  await expect(page.getByRole('heading', { name: '管理后台' })).toBeVisible()
  await expect(page.getByText('案件与律师')).toBeVisible()
  await expect(page.getByText('用户管理', { exact: true })).toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath(`admin-${testInfo.project.name}.png`),
    fullPage: true,
  })
})

test('lawyer can open the assigned-case dashboard', async ({ page }, testInfo) => {
  await login(page, 'lawyer', 'Lawyer123!')
  await expect(page.getByRole('heading', { name: '律师工作台' })).toBeVisible()
  await expect(page.getByText('这里只展示管理员已经分配给你的案件')).toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath(`lawyer-${testInfo.project.name}.png`),
    fullPage: true,
  })
})
