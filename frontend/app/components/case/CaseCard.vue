<template>
  <div
    class="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg transition-shadow cursor-pointer"
    @click="$emit('click', props.case)"
  >
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div class="flex-1">
        <h3 class="text-lg font-semibold text-gray-900 mb-1">
          {{ props.case.name }}
        </h3>
        <p v-if="props.case.case_number" class="text-sm text-gray-500 mb-1">
          Case #{{ props.case.case_number }}
        </p>
        <p v-if="props.case.client" class="text-sm text-gray-600">
          Client: {{ props.case.client }}
        </p>
      </div>

      <UBadge
        :color="getStatusColor(props.case.status)"
        variant="subtle"
      >
        {{ getStatusLabel(props.case.status) }}
      </UBadge>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <div class="text-center">
        <p class="text-2xl font-bold text-gray-900">{{ props.case.document_count || 0 }}</p>
        <p class="text-xs text-gray-500">Documents</p>
      </div>
      <div class="text-center">
        <p class="text-2xl font-bold text-gray-900">{{ formatFileSize(props.case.total_size || 0) }}</p>
        <p class="text-xs text-gray-500">Storage</p>
      </div>
      <div class="text-center">
        <p class="text-2xl font-bold text-gray-900">{{ props.case.entity_count || 0 }}</p>
        <p class="text-xs text-gray-500">Entities</p>
      </div>
    </div>

    <!-- Matter Type and Dates -->
    <div class="space-y-2 mb-4">
      <div v-if="props.case.matter_type" class="flex items-center text-sm text-gray-600">
        <UIcon name="i-heroicons-scale-20-solid" class="w-4 h-4 mr-2" />
        {{ props.case.matter_type }}
      </div>

      <div class="flex items-center text-sm text-gray-500">
        <UIcon name="i-heroicons-calendar-20-solid" class="w-4 h-4 mr-2" />
        Created {{ formatDate(props.case.created_at) }}
      </div>

      <div v-if="props.case.last_activity" class="flex items-center text-sm text-gray-500">
        <UIcon name="i-heroicons-clock-20-solid" class="w-4 h-4 mr-2" />
        Last activity {{ formatDate(props.case.last_activity) }}
      </div>
    </div>

    <!-- Progress Bar (for processing) -->
    <div v-if="props.case.status === 'processing'" class="mb-4">
      <div class="flex items-center justify-between text-sm text-gray-600 mb-1">
        <span>Processing documents...</span>
        <span>{{ props.case.progress || 0 }}%</span>
      </div>
      <UProgress :value="props.case.progress || 0" />
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <UButton
          variant="link"
          size="sm"
          @click.stop="$emit('click', props.case)"
        >
          <UIcon name="i-heroicons-eye-20-solid" class="w-4 h-4 mr-1" />
          View
        </UButton>

        <UDropdownMenu :items="getActionMenu()">
          <UButton variant="link" size="sm">
            <UIcon name="i-heroicons-ellipsis-vertical-20-solid" class="w-4 h-4" />
          </UButton>
        </UDropdownMenu>
      </div>

      <!-- Status Actions -->
      <div class="flex items-center space-x-2">
        <UButton
          v-if="props.case.status === 'unloaded'"
          variant="outline"
          size="sm"
          color="success"
          @click.stop="$emit('load', props.case)"
        >
          <UIcon name="i-heroicons-play-20-solid" class="w-4 h-4 mr-1" />
          Load
        </UButton>

        <UButton
          v-if="props.case.status === 'active'"
          variant="outline"
          size="sm"
          color="warning"
          @click.stop="$emit('unload', props.case)"
        >
          <UIcon name="i-heroicons-pause-20-solid" class="w-4 h-4 mr-1" />
          Unload
        </UButton>
      </div>
    </div>
  </div>
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
  click: [caseItem: Props['case']]
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