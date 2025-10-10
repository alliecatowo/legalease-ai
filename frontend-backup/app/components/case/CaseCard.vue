<template>
  <UPageCard
    :to="`/cases/${props.case.id}`"
    class="transition-all duration-200 hover:shadow-xl hover:scale-[1.02] group"
    :title="props.case.name"
    :description="getCaseDescription()"
  >
    <template #header>
      <div class="flex items-start justify-between">
        <div class="flex flex-wrap items-center gap-2">
          <UBadge
            v-if="props.case.case_number"
            variant="outline"
            size="sm"
          >
            #{{ props.case.case_number }}
          </UBadge>
          <UBadge
            v-if="props.case.client"
            variant="soft"
            size="sm"
            color="info"
          >
            {{ props.case.client }}
          </UBadge>
        </div>

        <UBadge
          :color="getStatusColor(props.case.status)"
          variant="solid"
          class="shrink-0"
        >
          {{ getStatusLabel(props.case.status) }}
        </UBadge>
      </div>
    </template>

    <!-- Key Metrics -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <UChip
        :text="`${props.case.document_count || 0}`"
        :description="'Documents'"
        icon="i-heroicons-document-text-20-solid"
        color="primary"
        size="lg"
      />
      <UChip
        :text="formatFileSize(props.case.total_size || 0)"
        :description="'Storage'"
        icon="i-heroicons-server-stack-20-solid"
        color="secondary"
        size="lg"
      />
      <UChip
        :text="`${props.case.entity_count || 0}`"
        :description="'Entities'"
        icon="i-heroicons-users-20-solid"
        color="success"
        size="lg"
      />
    </div>

    <!-- Case Details -->
    <div class="space-y-3 mb-6">
      <div v-if="props.case.matter_type" class="flex items-center text-sm text-gray-600">
        <UIcon name="i-heroicons-scale-20-solid" class="w-4 h-4 mr-3 text-primary" />
        <span class="font-medium">{{ props.case.matter_type }}</span>
      </div>

      <div class="flex items-center text-sm text-gray-500">
        <UIcon name="i-heroicons-calendar-days-20-solid" class="w-4 h-4 mr-3 text-info" />
        <span>Created {{ formatDate(props.case.created_at) }}</span>
      </div>

      <div v-if="props.case.last_activity" class="flex items-center text-sm text-gray-500">
        <UIcon name="i-heroicons-clock-20-solid" class="w-4 h-4 mr-3 text-warning" />
        <span>Last activity {{ formatDate(props.case.last_activity) }}</span>
      </div>
    </div>

    <!-- Progress Bar (for processing) -->
    <div v-if="props.case.status === 'processing'" class="mb-6">
      <div class="flex items-center justify-between text-sm text-gray-600 mb-2">
        <span class="font-medium">Processing documents...</span>
        <UBadge variant="outline" size="sm">
          {{ props.case.progress || 0 }}%
        </UBadge>
      </div>
      <UProgress :value="props.case.progress || 0" size="lg" />
    </div>

    <template #footer>
      <div class="flex items-center justify-between pt-4 border-t border-gray-100">
        <UDropdownMenu :items="getActionMenu()">
          <UButton variant="ghost" size="sm" color="gray">
            <UIcon name="i-heroicons-ellipsis-vertical-20-solid" class="w-4 h-4" />
          </UButton>
        </UDropdownMenu>

        <!-- Status Actions -->
        <div class="flex items-center space-x-2">
          <UButton
            v-if="props.case.status === 'unloaded'"
            variant="solid"
            size="sm"
            color="success"
            @click.stop="$emit('load', props.case)"
          >
            <UIcon name="i-heroicons-play-20-solid" class="w-4 h-4 mr-2" />
            Load
          </UButton>

          <UButton
            v-if="props.case.status === 'active'"
            variant="outline"
            size="sm"
            color="warning"
            @click.stop="$emit('unload', props.case)"
          >
            <UIcon name="i-heroicons-pause-20-solid" class="w-4 h-4 mr-2" />
            Unload
          </UButton>
        </div>
      </div>
    </template>
  </UPageCard>
</template>

<script setup lang="ts">

interface Props {
  case: {
    id: string
    name: string
    case_number?: string
    client?: string
    matter_type?: string
    status: string
    created_at: string
    last_activity?: string
    document_count?: number
    total_size?: number
    entity_count?: number
    progress?: number
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  load: [caseItem: Props['case']]
  unload: [caseItem: Props['case']]
  archive: [caseItem: Props['case']]
  delete: [caseItem: Props['case']]
}>()

// Methods
function getStatusColor(status: string): "primary" | "secondary" | "success" | "info" | "warning" | "error" | "neutral" {
  const colors: Record<string, "primary" | "secondary" | "success" | "info" | "warning" | "error" | "neutral"> = {
    active: 'success',
    unloaded: 'warning',
    archived: 'neutral',
    processing: 'info'
  }
  return colors[status] || 'neutral'
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: 'Active',
    unloaded: 'Unloaded',
    archived: 'Archived',
    processing: 'Processing'
  }
  return labels[status] || status
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffTime = Math.abs(now.getTime() - date.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

  if (diffDays === 1) {
    return 'today'
  } else if (diffDays === 2) {
    return 'yesterday'
  } else if (diffDays < 7) {
    return `${diffDays} days ago`
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7)
    return `${weeks} week${weeks > 1 ? 's' : ''} ago`
  } else {
    return date.toLocaleDateString()
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getCaseDescription(): string {
  const parts = []
  if (props.case.matter_type) parts.push(props.case.matter_type)
  if (props.case.last_activity) parts.push(`Last activity ${formatDate(props.case.last_activity)}`)
  return parts.length > 0 ? parts.join(' • ') : 'No recent activity'
}

function getActionMenu() {
  const menu = []

  if (props.case.status === 'active') {
    menu.push({
      label: 'Unload Case',
      icon: 'i-heroicons-pause-20-solid',
      click: () => emit('unload', props.case)
    })
  } else if (props.case.status === 'unloaded') {
    menu.push({
      label: 'Load Case',
      icon: 'i-heroicons-play-20-solid',
      click: () => emit('load', props.case)
    })
  }

  menu.push({
    label: 'Archive Case',
    icon: 'i-heroicons-archive-box-20-solid',
    click: () => emit('archive', props.case)
  })

  menu.push({
    label: 'Delete Case',
    icon: 'i-heroicons-trash-20-solid',
    click: () => emit('delete', props.case),
    class: 'text-red-600'
  })

  return menu
}
</script>