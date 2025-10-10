<template>
  <div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8">
      <header class="mb-8">
        <h1 class="text-4xl font-bold text-gray-900">
          LegalEase Dashboard
        </h1>
        <p class="mt-2 text-gray-600">
          AI-powered legal document analysis and compliance checking
        </p>
      </header>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <!-- Search Documents Card -->
        <div class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
          <div class="flex items-center mb-4">
            <UIcon name="i-heroicons-magnifying-glass-20-solid" class="w-8 h-8 text-blue-600 mr-3" />
            <h2 class="text-xl font-semibold">Search Documents</h2>
          </div>
          <p class="text-gray-600 mb-4">
            Hybrid search with AI-powered semantic understanding
          </p>
          <NuxtLink to="/search" class="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 inline-block text-center">
            Start Searching
          </NuxtLink>
        </div>

        <!-- Case Management Card -->
        <div class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
          <div class="flex items-center mb-4">
            <UIcon name="i-heroicons-folder-20-solid" class="w-8 h-8 text-green-600 mr-3" />
            <h2 class="text-xl font-semibold">Case Management</h2>
          </div>
          <p class="text-gray-600 mb-4">
            Organize documents by cases with load/unload capabilities
          </p>
          <NuxtLink to="/cases" class="w-full bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 inline-block text-center">
            Manage Cases
          </NuxtLink>
        </div>

        <!-- Transcription Card -->
        <div class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
          <div class="flex items-center mb-4">
            <UIcon name="i-heroicons-chat-bubble-left-right-20-solid" class="w-8 h-8 text-purple-600 mr-3" />
            <h2 class="text-xl font-semibold">Transcription</h2>
          </div>
          <p class="text-gray-600 mb-4">
            AI-powered audio/video transcription with speaker diarization
          </p>
          <button class="w-full bg-purple-600 text-white py-2 px-4 rounded hover:bg-purple-700">
            Upload Audio/Video
          </button>
        </div>

        <!-- Knowledge Graph Card -->
        <div class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
          <div class="flex items-center mb-4">
            <UIcon name="i-heroicons-share-20-solid" class="w-8 h-8 text-orange-600 mr-3" />
            <h2 class="text-xl font-semibold">Knowledge Graph</h2>
          </div>
          <p class="text-gray-600 mb-4">
            Visualize entity relationships and citation networks
          </p>
          <button class="w-full bg-orange-600 text-white py-2 px-4 rounded hover:bg-orange-700">
            Explore Graph
          </button>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="mt-8 bg-white rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold mb-4">System Overview</h3>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-600">{{ totalDocuments }}</div>
            <div class="text-sm text-gray-600">Total Documents</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-green-600">{{ activeCases }}</div>
            <div class="text-sm text-gray-600">Active Cases</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-purple-600">{{ totalTranscripts }}</div>
            <div class="text-sm text-gray-600">Transcripts</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-orange-600">{{ knowledgeGraphNodes }}</div>
            <div class="text-sm text-gray-600">Graph Nodes</div>
          </div>
        </div>
      </div>
    </div>
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
      totalDocuments.value = docsResponse.value.total || 0
    }

    if (casesResponse.status === 'fulfilled') {
      activeCases.value = casesResponse.value.active || 0
    }

    if (transcriptsResponse.status === 'fulfilled') {
      totalTranscripts.value = transcriptsResponse.value.total || 0
    }

    if (graphResponse.status === 'fulfilled') {
      knowledgeGraphNodes.value = graphResponse.value.nodes || 0
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
