<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  result: {
    id: string
    title: string
    excerpt: string
    documentType: string
    date: string
    jurisdiction?: string
    parties?: string[]
    citations?: number
    relevanceScore?: number
    entities?: Array<{ type: string; text: string }>
    caseNumber?: string
    court?: string
    metadata?: any
    vectorType?: string
    chunkType?: string
    pageNumber?: number
    filename?: string
  }
}>()

const typeConfig = computed(() => {
  const configs: Record<string, { icon: string; color: string; label: string; iconClass: string }> = {
    contract: { icon: 'i-lucide-file-text', color: 'primary', label: 'Contract', iconClass: 'text-primary' },
    court_filing: { icon: 'i-lucide-gavel', color: 'error', label: 'Court Filing', iconClass: 'text-error' },
    transcript: { icon: 'i-lucide-mic', color: 'info', label: 'Transcript', iconClass: 'text-info' },
    correspondence: { icon: 'i-lucide-mail', color: 'neutral', label: 'Correspondence', iconClass: 'text-neutral' },
    brief: { icon: 'i-lucide-file-pen', color: 'warning', label: 'Brief', iconClass: 'text-warning' },
    motion: { icon: 'i-lucide-file-check', color: 'success', label: 'Motion', iconClass: 'text-success' }
  }
  return configs[props.result.documentType] || { icon: 'i-lucide-file', color: 'neutral', label: 'Document', iconClass: 'text-neutral' }
})

const formattedDate = computed(() => {
  return new Date(props.result.date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
})

const entityColors: Record<string, string> = {
  PERSON: 'primary',
  ORGANIZATION: 'info',
  LOCATION: 'success',
  DATE: 'warning',
  MONEY: 'error',
  COURT: 'neutral',
  CITATION: 'secondary'
}

// Confidence score color and label
const confidenceConfig = computed(() => {
  const score = props.result.relevanceScore || 0
  const percentage = Math.round(score * 100)

  if (percentage >= 85) {
    return { color: 'success', label: 'Excellent Match', value: percentage }
  } else if (percentage >= 70) {
    return { color: 'primary', label: 'Good Match', value: percentage }
  } else if (percentage >= 50) {
    return { color: 'warning', label: 'Fair Match', value: percentage }
  } else {
    return { color: 'neutral', label: 'Weak Match', value: percentage }
  }
})

// Match type badge
const matchType = computed(() => {
  const vectorType = props.result.vectorType || 'unknown'
  if (vectorType === 'bm25') {
    return { label: 'Keyword', color: 'warning', icon: 'i-lucide-text-cursor-input' }
  } else if (vectorType.includes('summary') || vectorType.includes('section') || vectorType.includes('microblock')) {
    return { label: 'Semantic', color: 'primary', icon: 'i-lucide-sparkles' }
  } else {
    return { label: 'Hybrid', color: 'secondary', icon: 'i-lucide-zap' }
  }
})
</script>

<template>
  <UCard
    class="hover:shadow-lg transition-shadow cursor-pointer group"
    :ui="{ body: 'space-y-3' }"
  >
    <template #header>
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3 flex-1 min-w-0">
          <UIcon :name="typeConfig.icon" class="size-5 shrink-0 mt-0.5" :class="typeConfig.iconClass" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="font-semibold text-highlighted line-clamp-2 group-hover:text-primary transition-colors">
                {{ result.title }}
              </h3>
            </div>
            <div class="flex items-center gap-2 text-sm text-dimmed flex-wrap">
              <span>{{ formattedDate }}</span>
              <span v-if="result.jurisdiction">•</span>
              <span v-if="result.jurisdiction" class="capitalize">{{ result.jurisdiction }}</span>
              <span v-if="result.caseNumber">•</span>
              <span v-if="result.caseNumber">{{ result.caseNumber }}</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <UBadge :label="typeConfig.label" :color="typeConfig.color" variant="soft" size="sm" />
          <UTooltip text="Quick actions">
            <UButton
              icon="i-lucide-more-horizontal"
              color="neutral"
              variant="ghost"
              size="sm"
              class="opacity-0 group-hover:opacity-100 transition-opacity"
            />
          </UTooltip>
        </div>
      </div>
    </template>

    <!-- Match Type & Confidence Score -->
    <div class="flex items-center gap-3 pb-2 border-b border-default/50">
      <div class="flex items-center gap-1.5">
        <UIcon :name="matchType.icon" class="size-4 text-muted" />
        <span class="text-xs font-medium text-muted">{{ matchType.label }} Match</span>
      </div>
      <div class="flex-1 flex items-center gap-2">
        <UProgress
          :model-value="confidenceConfig.value"
          :color="confidenceConfig.color"
          size="sm"
          class="flex-1"
        />
        <span class="text-xs font-semibold text-highlighted tabular-nums">{{ confidenceConfig.value }}%</span>
      </div>
      <UTooltip :text="confidenceConfig.label">
        <UBadge
          :label="confidenceConfig.label"
          :color="confidenceConfig.color"
          variant="subtle"
          size="sm"
        />
      </UTooltip>
    </div>

    <!-- Excerpt with highlighting -->
    <div class="text-sm text-default">
      <p class="line-clamp-3" v-html="result.excerpt" />
      <p v-if="result.chunkType || result.pageNumber" class="text-xs text-dimmed mt-2 flex items-center gap-2">
        <span v-if="result.chunkType" class="flex items-center gap-1">
          <UIcon name="i-lucide-layers" class="size-3" />
          {{ result.chunkType }}
        </span>
        <span v-if="result.pageNumber">•</span>
        <span v-if="result.pageNumber" class="flex items-center gap-1">
          <UIcon name="i-lucide-file" class="size-3" />
          Page {{ result.pageNumber }}
        </span>
      </p>
    </div>

    <!-- Entities -->
    <div v-if="result.entities && result.entities.length" class="flex flex-wrap gap-1.5">
      <UBadge
        v-for="(entity, idx) in result.entities.slice(0, 8)"
        :key="idx"
        :label="entity.text"
        :color="entityColors[entity.type] || 'neutral'"
        variant="outline"
        size="sm"
      >
        <template #leading>
          <UIcon
            :name="entity.type === 'PERSON' ? 'i-lucide-user' : entity.type === 'ORGANIZATION' ? 'i-lucide-building' : entity.type === 'COURT' ? 'i-lucide-landmark' : 'i-lucide-tag'"
            class="size-3"
          />
        </template>
      </UBadge>
      <UBadge
        v-if="result.entities.length > 8"
        :label="`+${result.entities.length - 8} more`"
        color="neutral"
        variant="soft"
        size="sm"
      />
    </div>

    <!-- Metadata footer -->
    <template #footer>
      <div class="flex items-center justify-between text-sm">
        <div class="flex items-center gap-3 text-dimmed">
          <div v-if="result.parties" class="flex items-center gap-1">
            <UIcon name="i-lucide-users" class="size-4" />
            <span>{{ result.parties.length }} {{ result.parties.length === 1 ? 'party' : 'parties' }}</span>
          </div>
          <div v-if="result.citations" class="flex items-center gap-1">
            <UIcon name="i-lucide-link" class="size-4" />
            <span>{{ result.citations }} {{ result.citations === 1 ? 'citation' : 'citations' }}</span>
          </div>
          <div v-if="result.filename" class="flex items-center gap-1 max-w-xs">
            <UIcon name="i-lucide-file-text" class="size-4 shrink-0" />
            <span class="truncate">{{ result.filename }}</span>
          </div>
        </div>
        <div class="flex items-center gap-1">
          <UButton
            icon="i-lucide-plus-circle"
            color="neutral"
            variant="ghost"
            size="xs"
            label="Add to case"
          />
          <UButton
            icon="i-lucide-share"
            color="neutral"
            variant="ghost"
            size="xs"
          />
        </div>
      </div>
    </template>
  </UCard>
</template>
