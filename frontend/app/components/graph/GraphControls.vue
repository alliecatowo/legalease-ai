<script setup lang="ts">
const props = defineProps<{
  layout: 'cose' | 'circle' | 'grid' | 'breadthfirst' | 'concentric'
}>()

const emit = defineEmits<{
  'update:layout': [layout: 'cose' | 'circle' | 'grid' | 'breadthfirst' | 'concentric']
  'zoom-in': []
  'zoom-out': []
  'reset-zoom': []
  'fit': []
  'export': []
}>()

const layoutOptions = [
  { label: 'Force', value: 'cose', icon: 'i-lucide-network' },
  { label: 'Circle', value: 'circle', icon: 'i-lucide-circle-dot' },
  { label: 'Grid', value: 'grid', icon: 'i-lucide-grid-3x3' },
  { label: 'Tree', value: 'breadthfirst', icon: 'i-lucide-git-branch' },
  { label: 'Concentric', value: 'concentric', icon: 'i-lucide-radio' }
]
</script>

<template>
  <div class="flex items-center gap-2">
    <!-- Layout Selector -->
    <USelectMenu
      :model-value="layout"
      :items="layoutOptions"
      @update:model-value="(value) => emit('update:layout', value as any)"
      size="sm"
    >
      <template #label>
        <div class="flex items-center gap-2">
          <UIcon :name="layoutOptions.find(l => l.value === layout)?.icon || 'i-lucide-network'" class="size-4" />
          <span>{{ layoutOptions.find(l => l.value === layout)?.label }}</span>
        </div>
      </template>
    </USelectMenu>

    <USeparator orientation="vertical" class="h-6" />

    <!-- Zoom Controls -->
    <UFieldGroup>
      <UTooltip text="Zoom In">
        <UButton
          icon="i-lucide-zoom-in"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="emit('zoom-in')"
        />
      </UTooltip>
      <UTooltip text="Zoom Out">
        <UButton
          icon="i-lucide-zoom-out"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="emit('zoom-out')"
        />
      </UTooltip>
      <UTooltip text="Reset Zoom">
        <UButton
          icon="i-lucide-maximize"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="emit('reset-zoom')"
        />
      </UTooltip>
    </UFieldGroup>

    <USeparator orientation="vertical" class="h-6" />

    <!-- Fit to Screen -->
    <UTooltip text="Fit to Screen">
      <UButton
        icon="i-lucide-scan"
        label="Fit"
        color="neutral"
        variant="ghost"
        size="sm"
        @click="emit('fit')"
      />
    </UTooltip>

    <!-- Export -->
    <UTooltip text="Export as Image">
      <UButton
        icon="i-lucide-download"
        color="neutral"
        variant="ghost"
        size="sm"
        @click="emit('export')"
      />
    </UTooltip>
  </div>
</template>
