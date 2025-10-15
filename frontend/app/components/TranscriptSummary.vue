<script setup lang="ts">
const props = defineProps<{
  transcriptionId: number
  summary?: any
}>()

const api = useApi()
const isLoading = ref(false)
const isGenerating = ref(false)
const summaryData = ref(props.summary)

// Fetch summary if not provided
onMounted(async () => {
  if (!summaryData.value) {
    await fetchSummary()
  }
})

async function fetchSummary() {
  isLoading.value = true
  try {
    const response = await api.transcriptions.getSummary(props.transcriptionId)
    summaryData.value = response
  } catch (error) {
    console.error('Failed to fetch summary:', error)
  } finally {
    isLoading.value = false
  }
}

async function generateSummary() {
  isGenerating.value = true
  try {
    await api.transcriptions.generateSummary(props.transcriptionId)
    // Poll for completion
    await pollForSummary()
  } catch (error) {
    console.error('Failed to generate summary:', error)
    useToast().add({
      title: 'Error',
      description: 'Failed to generate summary',
      color: 'red'
    })
  } finally {
    isGenerating.value = false
  }
}

async function pollForSummary() {
  let attempts = 0
  const maxAttempts = 60 // 5 minutes

  while (attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 5000))
    await fetchSummary()

    if (summaryData.value?.executive_summary) {
      useToast().add({
        title: 'Success',
        description: 'Summary generated successfully',
        color: 'green'
      })
      return
    }
    attempts++
  }
}

const hasSummary = computed(() => {
  return summaryData.value?.executive_summary ||
         summaryData.value?.key_moments?.length > 0 ||
         summaryData.value?.timeline?.length > 0
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">AI Summary & Analysis</h2>
      <UButton
        v-if="!hasSummary"
        label="Generate Summary"
        icon="i-lucide-sparkles"
        :loading="isGenerating"
        @click="generateSummary"
      />
      <UButton
        v-else
        label="Regenerate"
        icon="i-lucide-refresh-cw"
        variant="outline"
        :loading="isGenerating"
        @click="generateSummary"
      />
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <UIcon name="i-lucide-loader-circle" class="size-8 animate-spin text-primary" />
    </div>

    <!-- No Summary State -->
    <UCard v-else-if="!hasSummary" :ui="{ body: 'text-center py-12' }">
      <UIcon name="i-lucide-file-text" class="size-16 text-muted mx-auto mb-4" />
      <h3 class="text-lg font-semibold mb-2">No Summary Available</h3>
      <p class="text-muted mb-4">
        Generate an AI-powered summary to get insights about this transcript
      </p>
      <UButton
        label="Generate Summary Now"
        icon="i-lucide-sparkles"
        :loading="isGenerating"
        @click="generateSummary"
      />
    </UCard>

    <!-- Summary Content -->
    <template v-else>
      <!-- Executive Summary -->
      <UCard v-if="summaryData?.executive_summary">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-file-text" class="size-5 text-primary" />
            <h3 class="font-semibold">Executive Summary</h3>
          </div>
        </template>
        <p class="text-sm leading-relaxed whitespace-pre-wrap">{{ summaryData.executive_summary }}</p>
      </UCard>

      <!-- Key Moments -->
      <UCard v-if="summaryData?.key_moments?.length">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-star" class="size-5 text-warning" />
            <h3 class="font-semibold">Key Moments</h3>
          </div>
        </template>
        <div class="space-y-3">
          <div
            v-for="(moment, idx) in summaryData.key_moments"
            :key="idx"
            class="flex gap-3 p-3 rounded-lg hover:bg-muted/50 transition"
          >
            <div class="flex-shrink-0">
              <UBadge :label="moment.timestamp" color="neutral" variant="soft" />
            </div>
            <div class="flex-1 space-y-1">
              <p class="text-sm font-medium">{{ moment.description }}</p>
              <p class="text-xs text-muted">{{ moment.importance }}</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Timeline -->
      <UCard v-if="summaryData?.timeline?.length">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-timeline" class="size-5 text-info" />
            <h3 class="font-semibold">Timeline</h3>
          </div>
        </template>
        <div class="space-y-2">
          <div
            v-for="(event, idx) in summaryData.timeline"
            :key="idx"
            class="flex gap-3 items-start"
          >
            <div class="flex-shrink-0 w-24 text-xs text-muted font-mono">
              {{ event.date }}
            </div>
            <div class="flex-1 text-sm">
              <p class="font-medium">{{ event.event }}</p>
              <p class="text-xs text-muted">{{ event.reference }}</p>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Speaker Stats -->
      <UCard v-if="summaryData?.speaker_stats">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-users" class="size-5 text-success" />
            <h3 class="font-semibold">Speaker Statistics</h3>
          </div>
        </template>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="(stats, speaker) in summaryData.speaker_stats"
            :key="speaker"
            class="p-4 rounded-lg border border-default"
          >
            <h4 class="font-semibold mb-2">{{ speaker }}</h4>
            <div class="space-y-1 text-sm">
              <div class="flex justify-between">
                <span class="text-muted">Speaking Time:</span>
                <span class="font-mono">{{ stats.speaking_time_formatted }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Word Count:</span>
                <span class="font-mono">{{ stats.word_count }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Segments:</span>
                <span class="font-mono">{{ stats.segment_count }}</span>
              </div>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Action Items -->
      <UCard v-if="summaryData?.action_items?.length">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-check-circle" class="size-5 text-primary" />
            <h3 class="font-semibold">Action Items & Decisions</h3>
          </div>
        </template>
        <div class="space-y-2">
          <div
            v-for="(item, idx) in summaryData.action_items"
            :key="idx"
            class="flex gap-3 p-3 rounded-lg border border-default"
          >
            <UBadge :label="item.type" color="primary" variant="soft" size="xs" />
            <div class="flex-1 space-y-1">
              <p class="text-sm font-medium">{{ item.description }}</p>
              <div class="flex gap-3 text-xs text-muted">
                <span v-if="item.responsible">👤 {{ item.responsible }}</span>
                <span v-if="item.deadline">📅 {{ item.deadline }}</span>
                <span v-if="item.timestamp">⏱️ {{ item.timestamp }}</span>
              </div>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Topics & Entities -->
      <UCard v-if="summaryData?.topics?.length || summaryData?.entities">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-tags" class="size-5 text-secondary" />
            <h3 class="font-semibold">Topics & Entities</h3>
          </div>
        </template>
        <div class="space-y-4">
          <div v-if="summaryData.topics?.length">
            <h4 class="text-sm font-medium mb-2">Topics Discussed</h4>
            <div class="flex flex-wrap gap-2">
              <UBadge
                v-for="topic in summaryData.topics"
                :key="topic"
                :label="topic"
                color="secondary"
                variant="soft"
              />
            </div>
          </div>

          <div v-if="summaryData.entities" class="space-y-3">
            <div v-if="summaryData.entities.parties?.length">
              <h4 class="text-sm font-medium mb-2">Parties</h4>
              <div class="flex flex-wrap gap-2">
                <UBadge
                  v-for="party in summaryData.entities.parties"
                  :key="party"
                  :label="party"
                  color="info"
                  variant="outline"
                  size="sm"
                />
              </div>
            </div>

            <div v-if="summaryData.entities.legal_terms?.length">
              <h4 class="text-sm font-medium mb-2">Legal Terms</h4>
              <div class="flex flex-wrap gap-2">
                <UBadge
                  v-for="term in summaryData.entities.legal_terms"
                  :key="term"
                  :label="term"
                  color="warning"
                  variant="outline"
                  size="sm"
                />
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </template>
  </div>
</template>
