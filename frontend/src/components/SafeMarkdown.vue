<template>
  <div class="markdown-body" v-html="rendered" />
</template>

<script setup lang="ts">
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const parser = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const rendered = computed(() =>
  DOMPurify.sanitize(parser.render(props.content || ''), {
    USE_PROFILES: { html: true },
  }),
)
</script>
