<template>
  <span
    class="brand-mark"
    :class="`brand-mark--${size}`"
    role="img"
    aria-label="劳务通"
  >
    <span aria-hidden="true">⚖️</span>
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: 'small' | 'large'
  }>(),
  {
    size: 'small',
  },
)
</script>
