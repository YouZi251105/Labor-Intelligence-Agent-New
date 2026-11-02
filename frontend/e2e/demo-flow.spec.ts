import { expect, type Page, test } from '@playwright/test'

const API_BASE_URL = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8000'

async function login(page: Page, username: string, password: string) {
  await page.goto('/login')
  await page.getByRole('textbox').first().fill(username)
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL((url) => url.pathname !== '/login')
}

async function createDemoCase(
  page: Page,
  title: string,
  moveToEvidence = false,
): Promise<number> {
  const token = await page.evaluate(() => localStorage.getItem('lia_token'))
  expect(token).toBeTruthy()
  const created = await page.request.post(`${API_BASE_URL}/api/v1/cases`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title,
      dispute_type: 'wage',
      location: '上海市',
      facts: '工作三个月，老板拖欠工资，正在准备材料。',
    },
  })
  expect(created.ok()).toBeTruthy()
  const caseId = (await created.json()).id as number

  if (moveToEvidence) {
    const consultation = await page.request.post(
      `${API_BASE_URL}/api/v1/cases/${caseId}/consultations`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { message: '老板拖欠工资两个月了，我需要准备什么？' },
      },
    )
    expect(consultation.ok()).toBeTruthy()
  }
  return caseId
}

test('login page is accessible', async ({ page }, testInfo) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '欢迎回来' })).toBeVisible()
  await expect(page.getByText('演示账号')).toHaveCount(0)
  await page.screenshot({
    path: `../docs/screenshots/login-${testInfo.project.name}.png`,
    fullPage: true,
  })
})

test('workspace stays usable at a 1366 by 768 viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  await login(page, 'demo', 'Demo123!')

  await expect(page.locator('.composer')).toBeInViewport()
  const layout = await page.evaluate(() => ({
    horizontalOverflow:
      document.documentElement.scrollWidth > document.documentElement.clientWidth,
    pageOverflow: document.querySelector<HTMLElement>('.page')?.scrollHeight
      ? document.querySelector<HTMLElement>('.page')!.scrollHeight >
        document.querySelector<HTMLElement>('.page')!.clientHeight
      : false,
    chatScrollable:
      (document.querySelector<HTMLElement>('.chat-message-list')?.scrollHeight ?? 0) >=
      (document.querySelector<HTMLElement>('.chat-message-list')?.clientHeight ?? 0),
  }))

  expect(layout.horizontalOverflow).toBe(false)
  expect(layout.pageOverflow).toBe(false)
  expect(layout.chatScrollable).toBe(true)
})

test('worker can consult, review a contract, and generate a document', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  await expect(page.locator('.workspace-header h1')).toBeVisible()
  await page.screenshot({
    path: testInfo.outputPath(`workspace-${testInfo.project.name}.png`),
    fullPage: true,
  })

  const caseId = await createDemoCase(
    page,
    `咨询文书流程-${testInfo.project.name}`,
    true,
  )
  const workflowResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET' &&
      /\/api\/v1\/cases\/\d+\/workflow$/.test(response.url()),
  )
  await page.goto(`/cases/${caseId}`)
  const workflowResponse = await workflowResponsePromise

  await expect(page.getByText('案件流程')).toBeVisible()
  expect(workflowResponse.ok()).toBeTruthy()
  await expect(page.locator('.workflow-step--current strong')).toHaveText('整理证据')
  await expect(page.getByRole('button', { name: '进入协商或仲裁' })).toBeDisabled()

  await page.getByRole('button', { name: '咨询记录' }).click()
  await page.locator('.chat-compose-inline textarea').fill('老板说这周还是不能发工资，我还需要准备什么？')
  const assistantCount = await page.locator('.chat-message--assistant').count()
  const consultationResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith(`/api/v1/cases/${caseId}/consultations`),
  )
  await page.getByRole('button', { name: '发送', exact: true }).click()
  const consultationResponse = await consultationResponsePromise
  expect(consultationResponse.ok()).toBeTruthy()
  await expect(page.locator('.chat-message--assistant')).toHaveCount(assistantCount + 1)
  await expect(page.locator('.chat-message--assistant .markdown-body').last()).not.toBeEmpty()

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
  await expect(page.getByText('证据四性评估')).toBeVisible()
  await expect(page.getByText('完整性')).toBeVisible()
  await expect(page.getByText('已提取').first()).toBeVisible()

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

test('workflow transitions are persisted by the backend', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  const caseId = await createDemoCase(
    page,
    `工作流持久化-${testInfo.project.name}`,
  )

  await page.goto(`/cases/${caseId}`)
  await expect(page.locator('.workflow-step--current strong')).toHaveText('识别问题')

  const transitionResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith(`/api/v1/cases/${caseId}/transitions`),
  )
  await page.getByRole('button', { name: '开始整理证据' }).click()
  const transitionResponse = await transitionResponsePromise
  expect(transitionResponse.ok()).toBeTruthy()
  await expect(page.locator('.workflow-step--current strong')).toHaveText('整理证据')

  await page.reload()
  await expect(page.locator('.workflow-step--current strong')).toHaveText('整理证据')
})

test('admin can open the management dashboard', async ({ page }, testInfo) => {
  await login(page, 'admin', 'Admin123!')
  await expect(page.getByRole('heading', { name: '管理后台' })).toBeVisible()
  await expect(page.locator('.metric-grid article').first().locator('strong')).not.toHaveText('0')
  const openNavigation = page.getByRole('button', { name: '打开导航' })
  if (await openNavigation.isVisible()) await openNavigation.click()
  await page.getByRole('link', { name: '用户管理', exact: true }).click()
  await expect(page).toHaveURL(/section=users/)
  await expect(page.getByRole('heading', { name: '用户管理' })).toBeVisible()
  await expect(page.getByPlaceholder('搜索用户名、姓名或手机号')).toBeVisible()
  await expect(page.locator('.sidebar--open')).toHaveCount(0)
  await page.screenshot({
    path: `../docs/screenshots/admin-${testInfo.project.name}.png`,
    fullPage: testInfo.project.name === 'desktop',
  })
})

test('lawyer can open the assigned-case dashboard', async ({ page }, testInfo) => {
  await login(page, 'lawyer', 'Lawyer123!')
  await expect(page.getByRole('heading', { name: '律师工作台' })).toBeVisible()
  await expect(page.getByText('这里只展示管理员已经分配给你的案件')).toBeVisible()
  await page.screenshot({
    path: `../docs/screenshots/lawyer-${testInfo.project.name}.png`,
    fullPage: true,
  })
})

test('evidence upload shows error for unsupported file type', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  const caseId = await createDemoCase(page, `异常-不支持类型-${testInfo.project.name}`, true)
  await page.goto(`/cases/${caseId}`)
  await page.getByRole('button', { name: '证据材料' }).click()
  await page.locator('input[type="file"]').setInputFiles({
    name: 'program.exe',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('MZ not-a-valid-upload'),
  })
  await expect(page.getByText(/不支持的文件类型/)).toBeVisible()
})

test('image evidence shows OCR-required status without OCR engine', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  const caseId = await createDemoCase(page, `异常-图片OCR-${testInfo.project.name}`, true)
  await page.goto(`/cases/${caseId}`)
  await page.getByRole('button', { name: '证据材料' }).click()
  const jpeg = Buffer.from(
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AVN//2Q==',
    'base64',
  )
  await page.locator('input[type="file"]').setInputFiles({
    name: '现场照片.jpg',
    mimeType: 'image/jpeg',
    buffer: jpeg,
  })
  await expect(page.getByText('待 OCR').first()).toBeVisible()
})

test('worker can practise a role simulation and receive coaching', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  const caseId = await createDemoCase(page, `模拟训练-${testInfo.project.name}`)
  await page.goto(`/simulation?caseId=${caseId}`)

  await expect(page.getByRole('heading', { name: '模拟对话训练' })).toBeVisible()
  await page.getByLabel('模拟角色').selectOption('boss')
  await page.getByLabel('训练场景').fill('向老板确认拖欠工资的支付时间')
  await page.getByRole('button', { name: '开始模拟' }).click()
  await page.getByLabel('你的表达').fill('请您确认9月和10月工资的支付时间，并书面确认金额。')
  await page.getByRole('button', { name: '发送并评分' }).click()

  await expect(page.getByText(/综合评分/)).toBeVisible()
  await expect(page.locator('.simulation-message--assistant')).toContainText('模拟')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: `../docs/screenshots/simulation-${testInfo.project.name}.png`,
    fullPage: true,
  })
})

test('help center shows official resources and site lawyers', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  await page.goto('/help')

  await expect(page.getByRole('heading', { name: '维权帮助' })).toBeVisible()
  await expect(page.getByText('全国人社政务服务平台')).toBeVisible()
  await expect(page.getByText('李律师')).toBeVisible()
  await expect(page.getByText('申请人工协助')).toBeVisible()
  await page.screenshot({
    path: `../docs/screenshots/help-${testInfo.project.name}.png`,
    fullPage: true,
  })
})
