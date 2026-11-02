import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SafeMarkdown from './SafeMarkdown.vue'

describe('SafeMarkdown', () => {
  it('renders common Markdown and removes executable content', () => {
    const wrapper = mount(SafeMarkdown, {
      props: {
        content:
          '**有限事实**\n\n- 工资流水\n- 聊天记录\n\n[官方入口](https://example.com)\n\n<script>alert(1)</script>\n\n[危险链接](javascript:alert(1))',
      },
    })

    expect(wrapper.find('strong').text()).toBe('有限事实')
    expect(wrapper.findAll('li')).toHaveLength(2)
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('a[href^="javascript:"]').exists()).toBe(false)
    expect(wrapper.find('a[href="https://example.com"]').attributes()).toMatchObject({
      target: '_blank',
      rel: 'noopener noreferrer',
    })
  })
})
