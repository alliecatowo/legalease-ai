<script setup lang="ts">
defineProps<{
  collapsed?: boolean
}>()
</script>

<template>
  <div class="px-2 py-3">
    <NuxtLink to="/" class="flex items-center gap-3" :class="collapsed ? 'justify-center' : ''">
      <UIcon name="i-lucide-scale" class="size-7 text-primary" />
      <span v-if="!collapsed" class="font-semibold text-lg">LegalEase</span>
    </NuxtLink>
  </div>
</template>
