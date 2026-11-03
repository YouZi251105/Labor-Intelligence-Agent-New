import { expect, type Page, test } from '@playwright/test'

const configuredBaseURL = process.env.PLAYWRIGHT_BASE_URL
const APP_BASE_URL = configuredBaseURL ?? 'http://127.0.0.1:5173'
const API_BASE_URL =
  process.env.PLAYWRIGHT_API_URL ??
  (configuredBaseURL ? new URL(configuredBaseURL).origin : 'http://127.0.0.1:8000')

async function waitForBrandImages(page: Page) {
  const images = page.locator('.brand-mark img, .auth-brand__logo img')
  await expect(images.first()).toBeVisible()
  await images.evaluateAll(async (elements) => {
    await Promise.all(
      elements.map(async (element) => {
        const image = element as HTMLImageElement
        if (!image.complete) {
          await new Promise<void>((resolve, reject) => {
            image.addEventListener('load', () => resolve(), { once: true })
            image.addEventListener('error', () => reject(new Error('brand image failed')), {
              once: true,
            })
          })
        }
        if (typeof image.decode === 'function') await image.decode()
      }),
    )
  })
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  )
}

async function login(page: Page, username: string, password: string) {
  await page.goto('/login')
  await page.getByRole('textbox').first().fill(username)
  await page.locator('input[type="password"]').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL((url) => url.pathname !== '/login')
  await waitForBrandImages(page)
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
  await waitForBrandImages(page)
  const brandLogo = page.locator('.auth-brand__logo img')
  await expect(brandLogo).toBeVisible()
  await expect
    .poll(() =>
      brandLogo.evaluate((image) => (image as HTMLImageElement).naturalWidth),
    )
    .toBeGreaterThan(128)
  await page.screenshot({
    path: `../docs/screenshots/login-${testInfo.project.name}.png`,
    fullPage: true,
  })
})

test('new worker must complete profile before entering core workspace', async ({ page }, testInfo) => {
  const username = `profile_gate_${testInfo.project.name}_${Date.now()}`
  await page.goto('/login')
  await page.getByRole('button', { name: '没有账号，立即注册' }).click()
  await page.locator('input[autocomplete="username"]').fill(username)
  await page.locator('.auth-form input:not([type="password"])').nth(1).fill('资料门槛用户')
  await page.locator('input[type="password"]').fill('ProfileGate123!')
  await page.locator('.auth-form button[type="submit"]').click()

  await expect(page).toHaveURL(/\/profile\?required=1/)
  await expect(page.getByRole('heading', { name: '请先完善个人资料' })).toBeVisible()
  await waitForBrandImages(page)
  await page.screenshot({
    path: `../docs/screenshots/profile-required-${testInfo.project.name}.png`,
    fullPage: false,
  })

  await page.goto('/')
  await expect(page).toHaveURL(/\/profile\?required=1/)

  await page.locator('input[autocomplete="name"]').fill('资料门槛用户')
  await page.locator('input[autocomplete="tel"]').fill('13900000000')
  await page.locator('input[autocomplete="off"][maxlength="18"]').fill('110101199001011234')
  await page.getByRole('button', { name: '保存并继续使用' }).click()

  await expect(page).toHaveURL((url) => url.origin === APP_BASE_URL && url.pathname === '/')
  await expect(page.locator('.workspace-header')).toBeVisible()
})

test('session expires after twenty minutes without activity', async ({ page }) => {
  await login(page, 'demo', 'Demo123!')
  await page.evaluate(() => {
    localStorage.setItem('lia_last_activity', String(Date.now() - 20 * 60 * 1000 - 1000))
  })
  await page.reload()

  await expect(page).toHaveURL(/\/login\?.*reason=idle/)
  await expect(page.getByText('因连续 20 分钟未操作，已自动退出登录。')).toBeVisible()
  await expect(page.locator('.app-shell')).toHaveCount(0)
})

test('workspace stays usable at 100 percent zoom', async ({ page }) => {
  await login(page, 'demo', 'Demo123!')

  for (const viewport of [
    { width: 1366, height: 768 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport)
    await page.goto('/')
    await expect(page.locator('.composer')).toBeInViewport()
    const layout = await page.evaluate(() => ({
      horizontalOverflow:
        document.documentElement.scrollWidth > document.documentElement.clientWidth,
      pageOverflow:
        (document.querySelector<HTMLElement>('.page')?.scrollHeight ?? 0) >
        (document.querySelector<HTMLElement>('.page')?.clientHeight ?? 0),
    }))

    expect(layout.horizontalOverflow).toBe(false)
    expect(layout.pageOverflow).toBe(false)
  }
})

test('simulation and help pages use one scroll layer at 100 percent zoom', async ({ page }) => {
  await login(page, 'demo', 'Demo123!')

  for (const viewport of [
    { width: 1366, height: 768 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport)
    for (const path of ['/simulation', '/help']) {
      await page.goto(path)
      await page.waitForTimeout(150)
      const layout = await page.evaluate(() => ({
        documentOverflow:
          document.documentElement.scrollHeight > document.documentElement.clientHeight,
        horizontalOverflow:
          document.documentElement.scrollWidth > document.documentElement.clientWidth,
      }))
      expect(layout.documentOverflow).toBe(false)
      expect(layout.horizontalOverflow).toBe(false)
    }
  }
})

test('worker can consult, review a contract, and generate a document', async ({ page }, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  const caseId = await createDemoCase(page, '工地欠薪咨询', true)
  await page.goto('/')
  await expect(page.locator('.workspace-header h1')).toHaveText('工地欠薪咨询')
  await waitForBrandImages(page)
  await page.screenshot({
    path: `../docs/screenshots/workspace-${testInfo.project.name}.png`,
    fullPage: true,
  })

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
  await expect(page.getByText('规则待复核', { exact: true })).toBeVisible()
  await expect(page.getByText('含待复核期限').first()).toBeVisible()
  await expect(page.getByRole('button', { name: '进入办理路径选择' })).toBeDisabled()

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
    path: `../docs/screenshots/case-workspace-${testInfo.project.name}.png`,
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
  await page.getByRole('button', { name: '先整理证据' }).click()
  const transitionResponse = await transitionResponsePromise
  expect(transitionResponse.ok()).toBeTruthy()
  await expect(page.locator('.workflow-step--current strong')).toHaveText('整理证据')

  await page.reload()
  await expect(page.locator('.workflow-step--current strong')).toHaveText('整理证据')
})

test('admin can open the management dashboard', async ({ page }, testInfo) => {
  await login(page, 'admin', 'Admin123!')
  await expect(page.getByRole('heading', { name: '运营数据大屏' })).toBeVisible()
  await expect(page.locator('.metric-grid article').first().locator('strong')).not.toHaveText('0')
  await expect(page.getByRole('heading', { name: '新增用户与案件' })).toBeVisible()
  await expect(page.locator('.dashboard-chart-grid canvas')).toHaveCount(3)
  await page.screenshot({
    path: `../docs/screenshots/admin-dashboard-${testInfo.project.name}.png`,
    fullPage: false,
  })
  const openNavigation = page.getByRole('button', { name: '打开导航' })
  if (await openNavigation.isVisible()) await openNavigation.click()
  await page.getByRole('link', { name: '用户管理', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/users$/)
  await expect(page.getByRole('heading', { level: 1, name: '用户管理' })).toBeVisible()
  await expect(page.getByPlaceholder('搜索用户名、姓名或手机号')).toBeVisible()
  await page.getByPlaceholder('搜索用户名、姓名或手机号').fill('demo')
  await expect(page.locator('.user-management-row')).toHaveCount(1)
  await expect(page.locator('.user-management-row').first()).toBeVisible()
  await page.locator('.user-management-row').first().getByRole('button', { name: '查看详情' }).click()
  await expect(page.locator('.user-management-detail')).toBeVisible()
  await expect(page.locator('.user-management-detail')).toContainText('身份证号')
  await expect(page.locator('.sidebar--open')).toHaveCount(0)
  await page.screenshot({
    path: `../docs/screenshots/admin-${testInfo.project.name}.png`,
    fullPage: testInfo.project.name === 'desktop',
  })
})

test('admin can validate a rule package', async ({ page }, testInfo) => {
  await login(page, 'admin', 'Admin123!')
  await page.goto('/admin/packages')

  await expect(
    page.getByRole('heading', { level: 1, name: '规则包中心' }),
  ).toBeVisible()
  await expect(page.locator('.rule-package-list__item').first()).toBeVisible()
  await expect(
    page.getByRole('button', { name: '下载 JSON 模板' }),
  ).toHaveCount(0)
  await expect(page.getByText('导入 JSON', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '载入模板' })).toHaveCount(0)
  await expect(page.locator('.rule-package-view-switch')).toHaveCount(0)
  await expect(page.getByText('JSON', { exact: true })).toHaveCount(0)
  await expect(page.getByText('导入 Excel', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'AI 生成草稿' }).click()
  await expect(page.getByRole('heading', { name: '描述需要的流程规则' })).toBeVisible()
  await expect(
    page.getByText('AI 会以当前内置规则包为基础生成草稿，生成后仍需人工复核校验。'),
  ).toBeVisible()
  await page.getByRole('button', { name: '取消', exact: true }).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载 Excel 模板' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe(
    'workflow-rule-package-template.xlsx',
  )
  const downloadedTemplate = testInfo.outputPath('workflow-template.xlsx')
  await download.saveAs(downloadedTemplate)
  await page
    .locator('input[accept*=".xlsx"]')
    .setInputFiles(downloadedTemplate)
  await expect(page.locator('.inline-error')).toContainText('规则包版本已存在')
  const pendingReviewPackage = page
    .locator('.rule-package-list__item')
    .filter({ hasText: '待复核' })
    .first()
  await expect(pendingReviewPackage).toBeVisible()
  await pendingReviewPackage.click()
  await expect(page.locator('.workflow-designer')).toBeVisible()
  await expect(page.locator('.workflow-designer__palette')).toHaveCount(0)
  await expect(page.locator('.workflow-block')).toHaveCount(6)
  await expect(page.locator('.workflow-designer input').first()).toBeDisabled()
  const wordDownloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载 Word 复核稿' }).click()
  const wordDownload = await wordDownloadPromise
  expect(wordDownload.suggestedFilename()).toMatch(/review\.docx$/)
  await page.getByRole('button', { name: '校验内容' }).click()

  await expect(page.getByText('结构校验通过')).toBeVisible()
  await expect(page.locator('.rule-package-summary')).toContainText(
    'cn-labor-workflow',
  )
  await page.evaluate(() => {
    window.scrollTo(0, 0)
    document.querySelector<HTMLElement>('.page')?.scrollTo(0, 0)
  })
  await page.screenshot({
    path: `../docs/screenshots/admin-rule-packages-${testInfo.project.name}.png`,
    fullPage: true,
  })
})

test('admin can compose workflow blocks by drag and drop', async ({
  page,
}, testInfo) => {
  await login(page, 'admin', 'Admin123!')
  const token = await page.evaluate(() => localStorage.getItem('lia_token'))
  expect(token).toBeTruthy()
  const version = `drag-${testInfo.project.name}-${Date.now()}`
  const template = await page.request.get(
    `${API_BASE_URL}/api/v1/admin/rule-packages/template`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  expect(template.ok()).toBeTruthy()
  const content = await template.json()
  content.version = version
  content.review_status = 'draft'
  const imported = await page.request.post(
    `${API_BASE_URL}/api/v1/admin/rule-packages/import`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { content },
    },
  )
  expect(imported.ok()).toBeTruthy()

  await page.goto('/admin/packages')
  const packageItem = page
    .locator('.rule-package-list__item')
    .filter({ hasText: version })
  await expect(packageItem).toBeVisible()
  await packageItem.click()
  await expect(page.locator('.workflow-designer__palette')).toBeVisible()
  await expect(
    page.getByText('草稿支持从左侧拖拽积木到画布', { exact: false }),
  ).toBeVisible()

  const initialBlocks = await page.locator('.workflow-block').count()
  const stageBlock = page
    .locator('.workflow-palette__item')
    .filter({ hasText: '阶段块' })
  if (testInfo.project.name === 'desktop') {
    await stageBlock.dragTo(page.locator('.workflow-designer__canvas'), {
      targetPosition: { x: 160, y: 560 },
    })
  } else {
    await stageBlock.click()
  }
  await expect(page.locator('.workflow-block')).toHaveCount(initialBlocks + 1)
})

test('admin navigation group collapses and remembers its state', async ({ page }, testInfo) => {
  await login(page, 'admin', 'Admin123!')
  const openNavigation = page.getByRole('button', { name: '打开导航' })
  if (testInfo.project.name === 'mobile') {
    await expect(openNavigation).toBeVisible()
    await openNavigation.click()
  }

  const adminToggle = page.getByRole('button', { name: '管理后台', exact: true })
  await expect(adminToggle).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('link', { name: '用户管理', exact: true })).toBeVisible()

  await adminToggle.click()
  await expect(adminToggle).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByRole('link', { name: '用户管理', exact: true })).toBeHidden()

  await page.reload()
  if (testInfo.project.name === 'mobile') {
    await expect(openNavigation).toBeVisible()
    await openNavigation.click()
  }
  await expect(adminToggle).toHaveAttribute('aria-expanded', 'false')

  await adminToggle.click()
  await expect(page.getByRole('link', { name: '用户管理', exact: true })).toBeVisible()
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

test('admin and lawyer help pages do not expose worker-only actions', async ({ page }) => {
  await login(page, 'admin', 'Admin123!')
  await page.goto('/help')
  await expect(page.getByRole('heading', { name: '平台资源维护' })).toBeVisible()
  await expect(page.getByText('本站律师', { exact: true })).toHaveCount(0)
  await expect(page.getByText('申请人工协助', { exact: true })).toHaveCount(0)

  await page.goto('/lawyer')
  await expect(page).toHaveURL((url) => url.origin === APP_BASE_URL && url.pathname === '/')

  await page.evaluate(() => localStorage.clear())
  await login(page, 'lawyer', 'Lawyer123!')
  await page.goto('/help')
  await expect(page.getByRole('heading', { name: '律师服务支持' })).toBeVisible()
  await expect(page.getByText('申请人工协助', { exact: true })).toHaveCount(0)
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

test('evidence deletion uses in-app confirmation and can be cancelled', async ({
  page,
}, testInfo) => {
  await login(page, 'demo', 'Demo123!')
  const caseId = await createDemoCase(page, `证据删除-${testInfo.project.name}`, true)
  await page.goto(`/cases/${caseId}`)
  await page.getByRole('button', { name: '证据材料' }).click()
  await page.locator('input[type="file"]').setInputFiles({
    name: '待删除工资记录.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('9月工资5000元，公司尚未支付。'),
  })

  const evidenceRow = page
    .locator('.evidence-list article')
    .filter({ hasText: '待删除工资记录.txt' })
  await expect(evidenceRow).toBeVisible()
  await evidenceRow.getByRole('button', { name: '删除', exact: true }).click()

  const dialog = page.locator('.el-message-box')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('删除材料', { exact: true })).toBeVisible()
  await page.waitForTimeout(250)
  await page.screenshot({
    path: `../docs/screenshots/evidence-delete-confirm-${testInfo.project.name}.png`,
    fullPage: false,
  })
  await dialog.getByRole('button', { name: '取消', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(evidenceRow).toBeVisible()

  await evidenceRow.getByRole('button', { name: '删除', exact: true }).click()
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: '删除', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(evidenceRow).toHaveCount(0)
  await expect(page.getByText('材料已删除')).toBeVisible()
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
