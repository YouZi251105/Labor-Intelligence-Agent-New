<template>
  <span
    class="brand-mark"
    :class="`brand-mark--${size}`"
    role="img"
    aria-label="劳务通"
  >
    <Scale
      :size="size === 'large' ? 30 : 22"
      :stroke-width="size === 'large' ? 2.5 : 2.3"
      color="#ffffff"
      aria-hidden="true"
    />
  </span>
</template>

<script setup lang="ts">
import { Scale } from '@lucide/vue'

withDefaults(
  defineProps<{
    size?: 'small' | 'large'
  }>(),
  {
    size: 'small',
  },
)
</script>
