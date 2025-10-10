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
  }
}>()

const typeConfig = computed(() => {
  const configs: Record<string, { icon: string; color: string; label: string }> = {
    contract: { icon: 'i-lucide-file-text', color: 'primary', label: 'Contract' },
    court_filing: { icon: 'i-lucide-gavel', color: 'error', label: 'Court Filing' },
    transcript: { icon: 'i-lucide-mic', color: 'info', label: 'Transcript' },
    correspondence: { icon: 'i-lucide-mail', color: 'neutral', label: 'Correspondence' },
    brief: { icon: 'i-lucide-file-pen', color: 'warning', label: 'Brief' },
    motion: { icon: 'i-lucide-file-check', color: 'success', label: 'Motion' }
  }
  return configs[props.result.documentType] || { icon: 'i-lucide-file', color: 'neutral', label: 'Document' }
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
</script>

<template>
  <UCard
    class="hover:shadow-lg transition-shadow cursor-pointer group"
    :ui="{ body: 'space-y-3' }"
  >
    <template #header>
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3 flex-1 min-w-0">
          <UIcon :name="typeConfig.icon" class="size-5 shrink-0 mt-0.5" :class="`text-${typeConfig.color}`" />
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

    <!-- Excerpt with highlighting -->
    <div class="text-sm text-default">
      <p class="line-clamp-3" v-html="result.excerpt" />
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
          <div v-if="result.relevanceScore" class="flex items-center gap-1">
            <UIcon name="i-lucide-sparkles" class="size-4" />
            <span>{{ Math.round(result.relevanceScore * 100) }}% match</span>
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
