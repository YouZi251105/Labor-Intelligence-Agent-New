<template>
  <div class="markdown-body" v-html="rendered" />
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

import { stabilizeStreamingMarkdown } from '../utils/streamingMarkdown'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const parser = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

parser.renderer.rules.link_open = (tokens, index, options, _env, renderer) => {
  tokens[index].attrSet('target', '_blank')
  tokens[index].attrSet('rel', 'noopener noreferrer')
  return renderer.renderToken(tokens, index, options)
}

const rendered = computed(() =>
  DOMPurify.sanitize(
    parser.render(
      props.streaming
        ? stabilizeStreamingMarkdown(props.content || '')
        : props.content || '',
    ),
    {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target'],
    },
  ),
)
</script>
