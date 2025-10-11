<script setup lang="ts">
interface Entity {
  type: string
  text: string
}

interface SearchResult {
  id: number
  title: string
  excerpt: string
  documentType: string
  date: string
  jurisdiction?: string
  relevanceScore: number
  entities?: Entity[]
  caseNumber?: string
  metadata?: any
  highlights?: string[]
  vectorType?: string
  chunkType?: string
  pageNumber?: number
  filename?: string
}

interface Props {
  result: SearchResult
}

const props = defineProps<Props>()

const router = useRouter()

type ColorType = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

// Document type configuration
const typeConfig = computed(() => {
  const configs: Record<string, { icon: string; color: ColorType; label: string }> = {
    contract: { icon: 'i-lucide-file-text', color: 'primary', label: 'Contract' },
    court_filing: { icon: 'i-lucide-gavel', color: 'error', label: 'Court Filing' },
    transcript: { icon: 'i-lucide-mic', color: 'warning', label: 'Transcript' },
    brief: { icon: 'i-lucide-file-pen', color: 'success', label: 'Brief' },
    motion: { icon: 'i-lucide-file-check', color: 'secondary', label: 'Motion' },
    correspondence: { icon: 'i-lucide-mail', color: 'info', label: 'Correspondence' },
    document: { icon: 'i-lucide-file', color: 'neutral', label: 'Document' }
  }
  return configs[props.result.documentType] || configs.document
})

// Entity type icons
const entityIcons: Record<string, string> = {
  PERSON: 'i-lucide-user',
  ORGANIZATION: 'i-lucide-building',
  LOCATION: 'i-lucide-map-pin',
  DATE: 'i-lucide-calendar',
  MONEY: 'i-lucide-dollar-sign',
  COURT: 'i-lucide-landmark',
  LAW: 'i-lucide-scale'
}

// Format date
const formattedDate = computed(() => {
  try {
    return new Date(props.result.date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  } catch {
    return props.result.date
  }
})

// Handle click - navigate to document with highlight
const handleClick = () => {
  const query: any = {}

  // Pass page number if available
  if (props.result.pageNumber) {
    query.page = props.result.pageNumber
  }

  // Pass chunk ID if available
  if (props.result.metadata?.chunk_id) {
    query.chunk = props.result.metadata.chunk_id
  }

  router.push({
    path: `/documents/${props.result.metadata?.document_id || props.result.id}`,
    query
  })
}

// Relevance score color
const scoreColor = computed((): ColorType => {
  if (props.result.relevanceScore >= 0.8) return 'success'
  if (props.result.relevanceScore >= 0.6) return 'info'
  if (props.result.relevanceScore >= 0.4) return 'warning'
  return 'neutral'
})
</script>

<template>
  <UCard
    class="search-result-card cursor-pointer hover:shadow-lg transition-all duration-200 hover:border-primary/50"
    @click="handleClick"
  >
    <div class="space-y-3">
      <!-- Header -->
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3 flex-1 min-w-0">
          <!-- Document Icon -->
          <div class="p-2 bg-muted/20 rounded-lg flex-shrink-0">
            <UIcon :name="typeConfig.icon" class="size-5" :class="`text-${typeConfig.color}`" />
          </div>

          <!-- Title and Metadata -->
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-highlighted text-lg mb-1 truncate">
              {{ result.title }}
            </h3>
            <div class="flex items-center gap-2 flex-wrap text-xs">
              <UBadge :label="typeConfig.label" :color="typeConfig.color" variant="soft" size="sm" />
              <span v-if="result.chunkType" class="text-muted">{{ result.chunkType }}</span>
              <span v-if="result.pageNumber" class="text-muted">Page {{ result.pageNumber }}</span>
              <span class="text-muted">{{ formattedDate }}</span>
              <span v-if="result.jurisdiction" class="text-muted">{{ result.jurisdiction }}</span>
            </div>
          </div>
        </div>

        <!-- Relevance Score -->
        <div class="flex-shrink-0">
          <UTooltip :text="`Relevance: ${(result.relevanceScore * 100).toFixed(0)}%`">
            <UBadge
              :label="`${(result.relevanceScore * 100).toFixed(0)}%`"
              :color="scoreColor"
              variant="subtle"
              size="sm"
            />
          </UTooltip>
        </div>
      </div>

      <!-- Excerpt with Highlights -->
      <div class="text-sm text-muted leading-relaxed">
        <div v-html="result.excerpt" />
      </div>

      <!-- Entities -->
      <div v-if="result.entities && result.entities.length > 0" class="flex flex-wrap gap-2">
        <UBadge
          v-for="(entity, idx) in result.entities.slice(0, 5)"
          :key="idx"
          :label="entity.text"
          color="neutral"
          variant="outline"
          size="sm"
        >
          <template #leading>
            <UIcon :name="entityIcons[entity.type] || 'i-lucide-tag'" class="size-3" />
          </template>
        </UBadge>
        <UBadge
          v-if="result.entities.length > 5"
          :label="`+${result.entities.length - 5} more`"
          color="neutral"
          variant="soft"
          size="sm"
        />
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between pt-2 border-t border-default/50">
        <div class="flex items-center gap-2 text-xs text-muted">
          <UIcon name="i-lucide-file" class="size-3" />
          <span>{{ result.filename || 'Document' }}</span>
        </div>
        <div class="flex items-center gap-2">
          <UBadge
            v-if="result.vectorType"
            :label="result.vectorType === 'bm25' ? 'Keyword' : 'Semantic'"
            :color="result.vectorType === 'bm25' ? 'warning' : 'primary'"
            variant="soft"
            size="sm"
          />
          <UIcon name="i-lucide-arrow-right" class="size-4 text-muted" />
        </div>
      </div>
    </div>
  </UCard>
</template>

<style scoped>
.search-result-card {
  transition: all 0.2s ease;
}

.search-result-card:hover {
  transform: translateY(-2px);
}
</style>
