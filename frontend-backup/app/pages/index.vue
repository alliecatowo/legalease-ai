<template>
  <div class="min-h-screen">
    <UPageSection>
      <header class="mb-8">
        <h1 class="text-4xl font-bold">
          LegalEase Dashboard
        </h1>
        <p class="mt-2 text-muted">
          AI-powered legal document analysis and compliance checking
        </p>
      </header>

      <UPageGrid>
        <!-- Search Documents Card -->
        <UPageCard
          title="Search Documents"
          description="Hybrid search with AI-powered semantic understanding"
          icon="i-heroicons-magnifying-glass-20-solid"
          to="/search"
        >
          <template #footer>
            <UButton color="primary" block>
              Start Searching
            </UButton>
          </template>
        </UPageCard>

        <!-- Case Management Card -->
        <UPageCard
          title="Case Management"
          description="Organize documents by cases with load/unload capabilities"
          icon="i-heroicons-folder-20-solid"
          to="/cases"
        >
          <template #footer>
            <UButton color="success" block>
              Manage Cases
            </UButton>
          </template>
        </UPageCard>

        <!-- Transcription Card -->
        <UPageCard
          title="Transcription"
          description="AI-powered audio/video transcription with speaker diarization"
          icon="i-heroicons-chat-bubble-left-right-20-solid"
        >
          <template #footer>
            <UButton color="info" block @click="showTranscriptionModal">
              Upload Audio/Video
            </UButton>
          </template>
        </UPageCard>

        <!-- Knowledge Graph Card -->
        <UPageCard
          title="Knowledge Graph"
          description="Visualize entity relationships and citation networks"
          icon="i-heroicons-share-20-solid"
        >
          <template #footer>
            <UButton color="warning" block @click="showKnowledgeGraphModal">
              Explore Graph
            </UButton>
          </template>
        </UPageCard>
      </UPageGrid>

      <!-- Quick Stats -->
      <UCard class="mt-8">
        <template #header>
          <h3 class="text-lg font-semibold">System Overview</h3>
        </template>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
          <UChip
            :text="totalDocuments.toString()"
            :description="'Total Documents'"
            icon="i-heroicons-document-text-20-solid"
            color="primary"
            size="lg"
          />
          <UChip
            :text="activeCases.toString()"
            :description="'Active Cases'"
            icon="i-heroicons-folder-20-solid"
            color="success"
            size="lg"
          />
          <UChip
            :text="totalTranscripts.toString()"
            :description="'Transcripts'"
            icon="i-heroicons-chat-bubble-left-right-20-solid"
            color="info"
            size="lg"
          />
          <UChip
            :text="knowledgeGraphNodes.toString()"
            :description="'Graph Nodes'"
            icon="i-heroicons-share-20-solid"
            color="warning"
            size="lg"
          />
        </div>
      </UCard>
    </UPageSection>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const { apiFetch } = useApi()

// Reactive state
const totalDocuments = ref(0)
const activeCases = ref(0)
const totalTranscripts = ref(0)
const knowledgeGraphNodes = ref(0)

// Methods
async function loadStats() {
  try {
    // Load system statistics
    const [docsResponse, casesResponse, transcriptsResponse, graphResponse] = await Promise.allSettled([
      apiFetch('/documents/stats'),
      apiFetch('/cases/stats'),
      apiFetch('/transcriptions/stats'),
      apiFetch('/graph/stats')
    ])

    if (docsResponse.status === 'fulfilled') {
      totalDocuments.value = (docsResponse.value as any)?.total || 0
    }

    if (casesResponse.status === 'fulfilled') {
      activeCases.value = (casesResponse.value as any)?.active || 0
    }

    if (transcriptsResponse.status === 'fulfilled') {
      totalTranscripts.value = (transcriptsResponse.value as any)?.total || 0
    }

    if (graphResponse.status === 'fulfilled') {
      knowledgeGraphNodes.value = (graphResponse.value as any)?.nodes || 0
    }

  } catch (error) {
    console.error('Failed to load dashboard stats:', error)
  }
}

// Lifecycle
onMounted(async () => {
  await loadStats()
})
</script>
