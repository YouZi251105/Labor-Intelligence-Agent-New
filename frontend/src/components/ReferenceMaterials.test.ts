import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ReferenceMaterials from './ReferenceMaterials.vue'
import type { ReferenceItem } from '../types/api'

const references: ReferenceItem[] = [
  {
    type: 'law',
    id: 'cn-labor-50',
    title: '《中华人民共和国劳动法》第五十条',
    excerpt: '工资应当以货币形式按月支付给劳动者本人。',
    source_name: '国家法律法规数据库',
    source_url: 'https://flk.npc.gov.cn/',
    review_status: 'published',
  },
  {
    type: 'case',
    id: 'case-cn-001',
    title: '苏州某供应链公司以券抵薪案',
    excerpt: '工资应当以货币形式支付。',
    source_name: '中国裁判文书网',
    source_url: 'https://wenshu.court.gov.cn/',
    review_status: 'published',
    case_no: '（2024）苏05民终1234号',
    court: '苏州市中级人民法院',
    year: 2024,
  },
]

describe('ReferenceMaterials', () => {
  it('renders nothing when there are no verified references', () => {
    const wrapper = mount(ReferenceMaterials, {
      props: { references: [] },
    })

    expect(wrapper.find('details').exists()).toBe(false)
    expect(wrapper.text()).toBe('')
  })

  it('renders a collapsed reference section by default', () => {
    const wrapper = mount(ReferenceMaterials, {
      props: { references },
    })

    const details = wrapper.find('details')
    expect(details.exists()).toBe(true)
    expect(details.attributes('open')).toBeUndefined()
    expect(details.text()).toContain('参考资料（2）')
    expect(details.text()).toContain('法律依据')
    expect(details.text()).toContain('相关类案')
    expect(wrapper.find('a[href="https://flk.npc.gov.cn/"]').attributes()).toMatchObject({
      target: '_blank',
      rel: 'noopener noreferrer',
    })
  })
})
