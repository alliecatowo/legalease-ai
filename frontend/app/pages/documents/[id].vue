<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Entity, BoundingBox } from '~/composables/usePDFHighlights'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const api = useApi()
const documentId = route.params.id as string

const highlights = usePDFHighlights()
const pdfViewerRef = ref<any>(null)

const document = ref<any>(null)
const isLoading = ref(true)
const activeTab = ref('viewer')
const showEntitySidebar = ref(true)

// Mock document data - TODO: Replace with real API call
const mockDocument = {
  id: documentId,
  title: 'Master Services Agreement - Acme Corp',
  filename: 'msa_acme_corp_2024.pdf',
  documentType: 'contract',
  uploadDate: '2024-01-15',
  fileSize: 2457600,
  pageCount: 15,
  status: 'processed',
  caseId: null,
  tags: ['contract', 'msa', 'active'],
  metadata: {
    parties: ['Acme Corporation', 'Global Tech Inc'],
    effectiveDate: '2024-01-15',
    expirationDate: '2025-01-15',
    jurisdiction: 'Delaware'
  }
}

// Mock entities - TODO: Get from backend
const mockEntities: Entity[] = [
  {
    id: 'entity-1',
    text: 'Acme Corporation',
    type: 'ORGANIZATION',
    confidence: 0.98,
    boundingBoxes: [
      { page: 1, x: 100, y: 150, width: 180, height: 20, text: 'Acme Corporation', type: 'entity', entityType: 'ORGANIZATION', id: 'box-1' },
      { page: 2, x: 150, y: 200, width: 180, height: 20, text: 'Acme Corporation', type: 'entity', entityType: 'ORGANIZATION', id: 'box-2' }
    ]
  },
  {
    id: 'entity-2',
    text: 'Global Tech Inc',
    type: 'ORGANIZATION',
    confidence: 0.96,
    boundingBoxes: [
      { page: 1, x: 300, y: 150, width: 160, height: 20, text: 'Global Tech Inc', type: 'entity', entityType: 'ORGANIZATION', id: 'box-3' }
    ]
  },
  {
    id: 'entity-3',
    text: 'January 15, 2024',
    type: 'DATE',
    confidence: 0.99,
    boundingBoxes: [
      { page: 1, x: 200, y: 100, width: 140, height: 20, text: 'January 15, 2024', type: 'entity', entityType: 'DATE', id: 'box-4' }
    ]
  },
  {
    id: 'entity-4',
    text: '$2,500,000',
    type: 'MONEY',
    confidence: 0.97,
    boundingBoxes: [
      { page: 3, x: 250, y: 300, width: 120, height: 20, text: '$2,500,000', type: 'entity', entityType: 'MONEY', id: 'box-5' }
    ]
  },
  {
    id: 'entity-5',
    text: 'Delaware',
    type: 'LOCATION',
    confidence: 0.95,
    boundingBoxes: [
      { page: 1, x: 150, y: 400, width: 100, height: 20, text: 'Delaware', type: 'entity', entityType: 'LOCATION', id: 'box-6' }
    ]
  }
]

// Load document data
async function loadDocument() {
  isLoading.value = true
  try {
    // TODO: Replace with real API call
    // const response = await api.documents.get(documentId)
    // document.value = response.data

    // Mock delay
    await new Promise(resolve => setTimeout(resolve, 500))
    document.value = mockDocument

    // Load entities
    mockEntities.forEach(entity => highlights.addEntity(entity))
  } catch (error) {
    console.error('Error loading document:', error)
  } finally {
    isLoading.value = false
  }
}

// Computed document URL
const documentUrl = computed(() => {
  if (!document.value) return ''
  // TODO: Replace with real document URL from backend
  return `/api/documents/${documentId}/download`
})

// Handle entity selection
function handleEntitySelect(entity: Entity) {
  highlights.selectEntity(entity)
  if (entity.boundingBoxes.length > 0) {
    const firstBox = entity.boundingBoxes[0]
    pdfViewerRef.value?.goToPage(firstBox.page)
  }
}

// Handle bounding box navigation
function handleNavigateToBox(boxId: string) {
  const entity = highlights.entities.value.find(e =>
    e.boundingBoxes.some(box => box.id === boxId)
  )
  if (entity) {
    const box = entity.boundingBoxes.find(b => b.id === boxId)
    if (box) {
      pdfViewerRef.value?.goToPage(box.page)
      highlights.selectEntity(entity)
    }
  }
}

// Handle box click from viewer
function handleBoxClick(box: BoundingBox) {
  const entity = highlights.entities.value.find(e =>
    e.boundingBoxes.some(b => b.id === box.id)
  )
  if (entity) {
    highlights.selectEntity(entity)
  }
}

// Get selected bounding box ID
const selectedBoxId = computed(() => {
  if (!highlights.selectedEntity.value) return null
  return highlights.selectedEntity.value.boundingBoxes[0]?.id || null
})

onMounted(() => {
  loadDocument()
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="document?.title || 'Document'">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            to="/documents"
          />
        </template>
        <template #trailing>
          <UButtonGroup>
            <UTooltip text="Add to Case">
              <UButton
                icon="i-lucide-folder-plus"
                color="neutral"
                variant="ghost"
              />
            </UTooltip>
            <UTooltip text="Share">
              <UButton
                icon="i-lucide-share"
                color="neutral"
                variant="ghost"
              />
            </UTooltip>
            <UTooltip text="Download">
              <UButton
                icon="i-lucide-download"
                color="neutral"
                variant="ghost"
              />
            </UTooltip>
            <UTooltip text="More">
              <UButton
                icon="i-lucide-more-horizontal"
                color="neutral"
                variant="ghost"
              />
            </UTooltip>
          </UButtonGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <div v-if="isLoading" class="flex items-center justify-center h-screen">
      <div class="text-center">
        <UIcon name="i-lucide-loader" class="size-12 text-primary animate-spin mb-4" />
        <p class="text-muted">Loading document...</p>
      </div>
    </div>

    <div v-else class="flex h-[calc(100vh-64px)]">
      <!-- Main Content -->
      <div class="flex-1 flex flex-col">
        <!-- Document Info Bar -->
        <div class="p-4 border-b border-default bg-default">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <UIcon name="i-lucide-file-text" class="size-5 text-primary" />
              <div>
                <h2 class="font-semibold text-highlighted">{{ document.title }}</h2>
                <p class="text-sm text-muted">
                  {{ document.pageCount }} pages •
                  {{ (document.fileSize / 1024 / 1024).toFixed(2) }} MB •
                  Uploaded {{ new Date(document.uploadDate).toLocaleDateString() }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <UBadge :label="document.documentType" color="primary" variant="soft" />
              <UBadge :label="document.status" color="success" variant="soft" />
            </div>
          </div>
        </div>

        <!-- Tabs -->
        <div class="border-b border-default">
          <UTabs
            :items="[
              { label: 'Viewer', value: 'viewer', icon: 'i-lucide-file-text' },
              { label: 'Analysis', value: 'analysis', icon: 'i-lucide-sparkles' },
              { label: 'Metadata', value: 'metadata', icon: 'i-lucide-info' },
              { label: 'History', value: 'history', icon: 'i-lucide-clock' }
            ]"
            v-model="activeTab"
          />
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-hidden">
          <!-- Viewer Tab -->
          <div v-if="activeTab === 'viewer'" class="h-full">
            <PDFViewerWithHighlights
              ref="pdfViewerRef"
              :document-url="documentUrl"
              :bounding-boxes="highlights.currentPageBoundingBoxes.value"
              :selected-box-id="selectedBoxId"
              @box-click="handleBoxClick"
              @box-hover="(box) => highlights.hoveredBoundingBox.value = box"
            />
          </div>

          <!-- Analysis Tab -->
          <div v-else-if="activeTab === 'analysis'" class="p-6 overflow-y-auto">
            <div class="max-w-4xl mx-auto space-y-6">
              <!-- AI Actions -->
              <div class="grid grid-cols-2 gap-4">
                <AiSparklesButton
                  action-type="summarize"
                  :target-id="documentId"
                  target-type="document"
                  block
                />
                <AiSparklesButton
                  action-type="analyze"
                  :target-id="documentId"
                  target-type="document"
                  block
                />
                <AiSparklesButton
                  action-type="extract"
                  :target-id="documentId"
                  target-type="document"
                  block
                />
                <AiSparklesButton
                  action-type="compare"
                  :target-id="documentId"
                  target-type="document"
                  label="Compare Documents"
                  block
                />
              </div>

              <UCard>
                <template #header>
                  <h3 class="font-semibold text-highlighted">AI Analysis Summary</h3>
                </template>
                <div class="prose prose-sm max-w-none">
                  <p class="text-default">
                    This is a Master Services Agreement between Acme Corporation and Global Tech Inc,
                    effective January 15, 2024. The agreement establishes terms for ongoing professional
                    services with a total contract value of $2,500,000.
                  </p>
                  <h4 class="text-highlighted">Key Terms:</h4>
                  <ul class="text-default">
                    <li>Contract Duration: 12 months</li>
                    <li>Payment Terms: Net 30</li>
                    <li>Governing Law: Delaware</li>
                    <li>Termination: 30 days notice</li>
                  </ul>
                </div>
              </UCard>

              <UCard>
                <template #header>
                  <h3 class="font-semibold text-highlighted">Extracted Clauses</h3>
                </template>
                <UAccordion
                  :items="[
                    { label: 'Indemnification', slot: 'indemnification' },
                    { label: 'Liability Limitations', slot: 'liability' },
                    { label: 'Confidentiality', slot: 'confidentiality' },
                    { label: 'Termination', slot: 'termination' }
                  ]"
                >
                  <template #indemnification>
                    <p class="text-sm text-default">
                      Each party agrees to indemnify and hold harmless the other party...
                    </p>
                  </template>
                  <template #liability>
                    <p class="text-sm text-default">
                      In no event shall either party's liability exceed the total fees paid...
                    </p>
                  </template>
                  <template #confidentiality>
                    <p class="text-sm text-default">
                      Both parties agree to maintain confidentiality of proprietary information...
                    </p>
                  </template>
                  <template #termination>
                    <p class="text-sm text-default">
                      Either party may terminate this agreement with 30 days written notice...
                    </p>
                  </template>
                </UAccordion>
              </UCard>
            </div>
          </div>

          <!-- Metadata Tab -->
          <div v-else-if="activeTab === 'metadata'" class="p-6 overflow-y-auto">
            <div class="max-w-2xl mx-auto">
              <UCard>
                <template #header>
                  <h3 class="font-semibold text-highlighted">Document Metadata</h3>
                </template>
                <div class="space-y-4">
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label class="text-sm font-medium text-muted">Document Type</label>
                      <p class="text-default">{{ document.documentType }}</p>
                    </div>
                    <div>
                      <label class="text-sm font-medium text-muted">Status</label>
                      <p class="text-default">{{ document.status }}</p>
                    </div>
                    <div>
                      <label class="text-sm font-medium text-muted">Upload Date</label>
                      <p class="text-default">{{ new Date(document.uploadDate).toLocaleDateString() }}</p>
                    </div>
                    <div>
                      <label class="text-sm font-medium text-muted">File Size</label>
                      <p class="text-default">{{ (document.fileSize / 1024 / 1024).toFixed(2) }} MB</p>
                    </div>
                  </div>

                  <div v-if="document.metadata.parties" class="pt-4 border-t border-default">
                    <label class="text-sm font-medium text-muted mb-2 block">Parties</label>
                    <div class="flex flex-wrap gap-2">
                      <UBadge
                        v-for="party in document.metadata.parties"
                        :key="party"
                        :label="party"
                        color="primary"
                        variant="soft"
                      />
                    </div>
                  </div>

                  <div v-if="document.tags" class="pt-4 border-t border-default">
                    <label class="text-sm font-medium text-muted mb-2 block">Tags</label>
                    <div class="flex flex-wrap gap-2">
                      <UBadge
                        v-for="tag in document.tags"
                        :key="tag"
                        :label="tag"
                        color="neutral"
                        variant="outline"
                      />
                    </div>
                  </div>
                </div>
              </UCard>
            </div>
          </div>

          <!-- History Tab -->
          <div v-else-if="activeTab === 'history'" class="p-6 overflow-y-auto">
            <div class="max-w-2xl mx-auto">
              <UTimeline
                :items="[
                  { title: 'Document uploaded', date: '2024-01-15 10:30 AM', icon: 'i-lucide-upload' },
                  { title: 'OCR processing completed', date: '2024-01-15 10:32 AM', icon: 'i-lucide-scan' },
                  { title: 'Entity extraction completed', date: '2024-01-15 10:35 AM', icon: 'i-lucide-tag' },
                  { title: 'AI analysis completed', date: '2024-01-15 10:40 AM', icon: 'i-lucide-sparkles' }
                ]"
                :default-value="3"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Entity Sidebar -->
      <div
        v-if="activeTab === 'viewer' && showEntitySidebar"
        class="w-80 border-l border-default bg-default overflow-hidden"
      >
        <EntitySidebar
          :entities="highlights.entities.value"
          :selected-entity="highlights.selectedEntity.value"
          @select-entity="handleEntitySelect"
          @navigate-to-box="handleNavigateToBox"
        />
      </div>

      <!-- Sidebar Toggle Button (when collapsed) -->
      <div
        v-if="activeTab === 'viewer' && !showEntitySidebar"
        class="fixed right-0 top-1/2 -translate-y-1/2"
      >
        <UButton
          icon="i-lucide-panel-right"
          color="neutral"
          variant="soft"
          @click="showEntitySidebar = true"
        />
      </div>
    </div>
  </UDashboardPanel>
</template>
