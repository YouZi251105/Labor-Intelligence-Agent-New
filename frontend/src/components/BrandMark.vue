<template>
  <span
    class="brand-mark"
    :class="`brand-mark--${size}`"
    role="img"
    aria-label="劳务通"
  >
    <picture>
      <source srcset="/brand/labor-mark.webp" type="image/webp" />
      <img src="/brand/labor-mark.png" alt="" aria-hidden="true" />
    </picture>
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
