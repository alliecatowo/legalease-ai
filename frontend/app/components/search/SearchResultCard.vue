<template>
  <div
    class="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
    @click="$emit('click', result)"
  >
    <!-- Header -->
    <div class="flex items-start justify-between mb-3">
      <div class="flex-1">
        <h3 class="text-lg font-semibold text-gray-900 mb-1">
          {{ result.filename }}
        </h3>
        <div class="flex items-center space-x-4 text-sm text-gray-500">
          <span class="flex items-center">
            <UIcon name="i-heroicons-folder-20-solid" class="w-4 h-4 mr-1" />
            {{ result.case_name }}
          </span>
          <span class="flex items-center">
            <UIcon name="i-heroicons-clock-20-solid" class="w-4 h-4 mr-1" />
            {{ formatDate(result.created_at) }}
          </span>
          <span class="flex items-center">
            <UIcon name="i-heroicons-document-20-solid" class="w-4 h-4 mr-1" />
            {{ formatFileSize(result.size) }}
          </span>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <UBadge
          :color="getTypeColor(result.doc_type)"
          variant="subtle"
        >
          {{ result.doc_type || 'document' }}
        </UBadge>
        <USBadge
          :color="getScoreColor(result.score)"
          variant="subtle"
        >
          {{ Math.round(result.score * 100) }}%
        </USBadge>
      </div>
    </div>

    <!-- Snippet -->
    <div v-if="result.snippet" class="mb-4">
      <p class="text-gray-700 text-sm leading-relaxed">
        <span v-html="highlightSnippet(result.snippet, result.highlights)" />
      </p>
    </div>

    <!-- Tags -->
    <div v-if="result.tags && result.tags.length > 0" class="mb-4">
      <div class="flex flex-wrap gap-1">
        <UBadge
          v-for="tag in result.tags.slice(0, 5)"
          :key="tag"
          variant="outline"
          size="sm"
        >
          {{ tag }}
        </UBadge>
        <UBadge
          v-if="result.tags.length > 5"
          variant="outline"
          size="sm"
        >
          +{{ result.tags.length - 5 }} more
        </UBadge>
      </div>
    </div>

    <!-- Entities -->
    <div v-if="result.entities && result.entities.length > 0" class="mb-4">
      <div class="text-xs text-gray-500 mb-2">Key entities:</div>
      <div class="flex flex-wrap gap-1">
        <UBadge
          v-for="entity in result.entities.slice(0, 6)"
          :key="entity.text"
          :color="getEntityColor(entity.type)"
          variant="subtle"
          size="sm"
        >
          {{ entity.text }}
        </UBadge>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <UButton
          variant="link"
          size="sm"
          @click.stop="summarizeDocument"
        >
          <UIcon name="i-heroicons-document-text-20-solid" class="w-4 h-4 mr-1" />
          Summarize
        </UButton>
        <UButton
          variant="link"
          size="sm"
          @click.stop="viewTranscript"
        >
          <UIcon name="i-heroicons-chat-bubble-left-right-20-solid" class="w-4 h-4 mr-1" />
          Transcript
        </UButton>
        <UButton
          variant="link"
          size="sm"
          @click.stop="downloadDocument"
        >
          <UIcon name="i-heroicons-arrow-down-tray-20-solid" class="w-4 h-4 mr-1" />
          Download
        </UButton>
      </div>

      <div class="flex items-center space-x-1">
        <UButton
          variant="ghost"
          size="sm"
          @click.stop="toggleBookmark"
        >
          <UIcon
            :name="result.bookmarked ? 'i-heroicons-bookmark-20-solid' : 'i-heroicons-bookmark-20-solid'"
            :class="result.bookmarked ? 'w-4 h-4 text-blue-600' : 'w-4 h-4 text-gray-400'"
          />
        </UButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">

interface Props {
  result: {
    id: string
    filename: string
    case_name: string
    created_at: string
    size: number
    doc_type?: string
    score: number
    snippet?: string
    highlights?: string[]
    tags?: string[]
    entities?: Array<{ text: string; type: string }>
    bookmarked?: boolean
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  click: [result: Props['result']]
}>()

// Methods
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString()
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getTypeColor(type?: string): string {
  const colors: Record<string, string> = {
    contract: 'blue',
    lawsuit: 'red',
    court_order: 'purple',
    statute: 'green',
    evidence: 'orange',
    correspondence: 'gray'
  }
  return colors[type || ''] || 'gray'
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'green'
  if (score >= 0.6) return 'yellow'
  return 'red'
}

function getEntityColor(type: string): string {
  const colors: Record<string, string> = {
    PERSON: 'blue',
    ORGANIZATION: 'purple',
    COURT: 'green',
    DATE: 'orange',
    AMOUNT: 'red',
    CITATION: 'indigo'
  }
  return colors[type] || 'gray'
}

function highlightSnippet(snippet: string, highlights: string[] = []): string {
  let highlighted = snippet

  if (highlights && highlights.length > 0) {
    highlights.forEach(term => {
      const regex = new RegExp(`(${escapeRegex(term)})`, 'gi')
      highlighted = highlighted.replace(regex, '<mark class="bg-yellow-200">$1</mark>')
    })
  }

  return highlighted
}

function escapeRegex(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function summarizeDocument() {
  // TODO: Implement document summarization
  console.log('Summarize document:', props.result.id)
}

async function viewTranscript() {
  // TODO: Implement transcript view
  console.log('View transcript:', props.result.id)
}

async function downloadDocument() {
  // TODO: Implement document download
  console.log('Download document:', props.result.id)
}

async function toggleBookmark() {
  // TODO: Implement bookmarking
  console.log('Toggle bookmark:', props.result.id)
}
</script>