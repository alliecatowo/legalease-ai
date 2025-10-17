<script setup lang="ts">
definePageMeta({
  layout: 'default'
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar title="Activity">
      </UDashboardNavbar>
    </template>

    <div class="overflow-y-auto h-[calc(100vh-64px)]">
      <div class="max-w-7xl mx-auto p-6 space-y-6">
        <div class="text-center py-20">
          <UIcon name="i-lucide-activity" class="size-20 text-muted mx-auto mb-6 opacity-30" />
          <h3 class="text-2xl font-semibold mb-3 text-highlighted">Activity Feed</h3>
          <p class="text-muted mb-6 max-w-md mx-auto">
            Track all actions and changes across your cases and documents.
          </p>
          <p class="text-sm text-dimmed">Coming soon...</p>
        </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
