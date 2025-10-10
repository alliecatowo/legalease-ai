<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const caseId = route.params.id

// Mock case data - TODO: Fetch from API based on caseId
const caseData = ref({
  id: caseId,
  name: 'Acme Corp v. Global Tech Inc',
  caseNumber: '2024-CV-12345',
  type: 'Civil Litigation',
  status: 'active',
  court: 'Superior Court of California',
  jurisdiction: 'California',
  openedDate: '2024-01-15',
  lastActivity: '2024-03-10',
  description: 'Breach of contract dispute involving software licensing agreements between Acme Corporation and Global Tech Inc. The plaintiff alleges breach of a master services agreement and seeks damages of $2.5M plus attorney fees.',
  tags: ['contract', 'software', 'licensing', 'breach'],
  parties: [
    { id: '1', name: 'Acme Corporation', role: 'Plaintiff', type: 'organization', email: 'legal@acmecorp.com' },
    { id: '2', name: 'Global Tech Inc', role: 'Defendant', type: 'organization', email: 'legal@globaltech.com' },
    { id: '3', name: 'Jane Smith', role: 'Plaintiff Attorney', type: 'person', email: 'jsmith@lawfirm.com' },
    { id: '4', name: 'John Doe', role: 'Defendant Attorney', type: 'person', email: 'jdoe@defense.com' }
  ],
  documents: [
    { id: '1', name: 'Master Services Agreement.pdf', type: 'contract', uploadedDate: '2024-01-15', size: '2.3 MB', status: 'analyzed' },
    { id: '2', name: 'Complaint.pdf', type: 'court_filing', uploadedDate: '2024-01-16', size: '1.8 MB', status: 'analyzed' },
    { id: '3', name: 'Answer to Complaint.pdf', type: 'court_filing', uploadedDate: '2024-02-01', size: '1.5 MB', status: 'analyzing' },
    { id: '4', name: 'Discovery Request.pdf', type: 'motion', uploadedDate: '2024-02-15', size: '892 KB', status: 'pending' },
    { id: '5', name: 'Email Correspondence.pdf', type: 'correspondence', uploadedDate: '2024-03-01', size: '654 KB', status: 'analyzed' }
  ],
  timeline: [
    { date: '2024-01-15', event: 'Case Filed', description: 'Complaint filed with Superior Court', type: 'filing' },
    { date: '2024-01-20', event: 'Summons Served', description: 'Defendant served with summons and complaint', type: 'service' },
    { date: '2024-02-01', event: 'Answer Filed', description: 'Defendant filed answer to complaint', type: 'filing' },
    { date: '2024-02-15', event: 'Discovery Initiated', description: 'Plaintiff served initial discovery requests', type: 'discovery' },
    { date: '2024-03-15', event: 'Discovery Response Due', description: 'Defendant responses to discovery due', type: 'deadline' },
    { date: '2024-04-01', event: 'Case Management Conference', description: 'Scheduled CMC with Judge Anderson', type: 'hearing' }
  ],
  deadlines: [
    { date: '2024-03-15', title: 'Discovery Response Due', priority: 'high', completed: false },
    { date: '2024-04-01', title: 'Case Management Conference', priority: 'high', completed: false },
    { date: '2024-04-15', title: 'Expert Designation Due', priority: 'medium', completed: false }
  ],
  notes: [
    { id: '1', author: 'Jane Smith', date: '2024-03-10', content: 'Client meeting scheduled for next week to review discovery responses' },
    { id: '2', author: 'John Doe', date: '2024-03-08', content: 'Opposing counsel requested extension on discovery - denied' }
  ]
})

const activeTab = ref('overview')

const tabs = [
  { label: 'Overview', value: 'overview', icon: 'i-lucide-layout-dashboard' },
  { label: 'Documents', value: 'documents', icon: 'i-lucide-files', badge: caseData.value.documents.length },
  { label: 'Timeline', value: 'timeline', icon: 'i-lucide-calendar' },
  { label: 'Parties', value: 'parties', icon: 'i-lucide-users' },
  { label: 'Graph', value: 'graph', icon: 'i-lucide-network' },
  { label: 'Notes', value: 'notes', icon: 'i-lucide-sticky-note' }
]

const statusColors: Record<string, string> = {
  active: 'success',
  pending: 'warning',
  closed: 'neutral'
}

const documentTypeIcons: Record<string, string> = {
  contract: 'i-lucide-file-text',
  court_filing: 'i-lucide-gavel',
  motion: 'i-lucide-file-check',
  correspondence: 'i-lucide-mail',
  transcript: 'i-lucide-mic'
}

const timelineTypeColors: Record<string, string> = {
  filing: 'primary',
  service: 'info',
  discovery: 'warning',
  deadline: 'error',
  hearing: 'success'
}

const upcomingDeadlines = computed(() => {
  return caseData.value.deadlines
    .filter(d => !d.completed && new Date(d.date) >= new Date())
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
})
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar>
        <template #leading>
          <div class="flex items-center gap-3">
            <UButton
              icon="i-lucide-arrow-left"
              color="neutral"
              variant="ghost"
              to="/cases"
            />
            <div>
              <h1 class="font-semibold text-lg">{{ caseData.name }}</h1>
              <p class="text-sm text-dimmed">{{ caseData.caseNumber }}</p>
            </div>
          </div>
        </template>
        <template #trailing>
          <UButtonGroup>
            <UButton
              icon="i-lucide-brain"
              color="primary"
              variant="solid"
              label="Deep Research"
              :to="`/cases/${caseId}/research`"
            >
              <template #leading>
                <UIcon name="i-lucide-sparkles" class="animate-pulse" />
              </template>
            </UButton>
            <UButton icon="i-lucide-share" color="neutral" variant="outline" label="Share" />
            <UButton icon="i-lucide-download" color="neutral" variant="outline" label="Export" />
            <UDropdownMenu>
              <UButton icon="i-lucide-more-vertical" color="neutral" variant="ghost" />
              <template #content>
                <div class="p-1">
                  <UButton label="Edit Case" icon="i-lucide-pencil" color="neutral" variant="ghost" block />
                  <UButton label="Close Case" icon="i-lucide-folder-x" color="neutral" variant="ghost" block />
                  <USeparator class="my-1" />
                  <UButton label="Delete Case" icon="i-lucide-trash-2" color="error" variant="ghost" block />
                </div>
              </template>
            </UDropdownMenu>
          </UButtonGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <!-- Case Header -->
    <div class="p-6 border-b border-default">
      <div class="flex flex-col lg:flex-row gap-6">
        <div class="flex-1 space-y-4">
          <div class="flex items-start gap-3">
            <UIcon name="i-lucide-briefcase" class="size-12 text-primary" />
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <UBadge :label="caseData.status" :color="statusColors[caseData.status]" variant="soft" class="capitalize" />
                <UBadge :label="caseData.type" color="neutral" variant="outline" />
              </div>
              <p class="text-default">{{ caseData.description }}</p>
              <div class="flex flex-wrap gap-2 mt-3">
                <UBadge v-for="tag in caseData.tags" :key="tag" :label="tag" size="sm" variant="outline" />
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p class="text-xs text-muted mb-1">Court</p>
              <p class="font-medium text-sm">{{ caseData.court }}</p>
            </div>
            <div>
              <p class="text-xs text-muted mb-1">Jurisdiction</p>
              <p class="font-medium text-sm">{{ caseData.jurisdiction }}</p>
            </div>
            <div>
              <p class="text-xs text-muted mb-1">Filed</p>
              <p class="font-medium text-sm">{{ new Date(caseData.openedDate).toLocaleDateString() }}</p>
            </div>
            <div>
              <p class="text-xs text-muted mb-1">Last Activity</p>
              <p class="font-medium text-sm">{{ new Date(caseData.lastActivity).toLocaleDateString() }}</p>
            </div>
          </div>
        </div>

        <div class="lg:w-80 space-y-3">
          <UCard v-if="upcomingDeadlines.length" :ui="{ body: 'p-4' }">
            <div class="flex items-center gap-2 mb-3">
              <UIcon name="i-lucide-alert-circle" class="size-5 text-error" />
              <h3 class="font-semibold">Upcoming Deadlines</h3>
            </div>
            <div class="space-y-2">
              <div v-for="deadline in upcomingDeadlines.slice(0, 3)" :key="deadline.date" class="flex items-start justify-between gap-2">
                <div class="flex-1">
                  <p class="text-sm font-medium">{{ deadline.title }}</p>
                  <p class="text-xs text-muted">{{ new Date(deadline.date).toLocaleDateString() }}</p>
                </div>
                <UBadge :label="deadline.priority" :color="deadline.priority === 'high' ? 'error' : 'warning'" size="xs" />
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </div>

    <!-- Tabs Navigation -->
    <div class="border-b border-default">
      <UContainer>
        <UTabs v-model="activeTab" :items="tabs" class="w-full">
          <template #default="{ item }">
            <div class="flex items-center gap-2">
              <UIcon :name="item.icon" class="size-4" />
              <span>{{ item.label }}</span>
              <UBadge v-if="item.badge" :label="String(item.badge)" size="xs" variant="soft" />
            </div>
          </template>
        </UTabs>
      </UContainer>
    </div>

    <!-- Tab Content -->
    <div class="p-6">
      <UContainer>
        <!-- Overview Tab -->
        <div v-if="activeTab === 'overview'" class="space-y-6">
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Quick Stats -->
            <UCard>
              <template #header>
                <h3 class="font-semibold">Quick Stats</h3>
              </template>
              <div class="space-y-4">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted">Documents</span>
                  <span class="font-semibold">{{ caseData.documents.length }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted">Parties</span>
                  <span class="font-semibold">{{ caseData.parties.length }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted">Timeline Events</span>
                  <span class="font-semibold">{{ caseData.timeline.length }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted">Open Deadlines</span>
                  <span class="font-semibold">{{ upcomingDeadlines.length }}</span>
                </div>
              </div>
            </UCard>

            <!-- Recent Documents -->
            <UCard class="lg:col-span-2">
              <template #header>
                <div class="flex items-center justify-between">
                  <h3 class="font-semibold">Recent Documents</h3>
                  <UButton label="View All" size="xs" color="neutral" variant="ghost" @click="activeTab = 'documents'" />
                </div>
              </template>
              <div class="space-y-2">
                <div v-for="doc in caseData.documents.slice(0, 4)" :key="doc.id" class="flex items-center gap-3 p-2 rounded-lg hover:bg-elevated/50 transition-colors">
                  <UIcon :name="documentTypeIcons[doc.type] || 'i-lucide-file'" class="size-5 text-primary" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ doc.name }}</p>
                    <p class="text-xs text-dimmed">{{ doc.size }} • {{ new Date(doc.uploadedDate).toLocaleDateString() }}</p>
                  </div>
                  <UBadge :label="doc.status" size="xs" variant="soft" />
                </div>
              </div>
            </UCard>
          </div>

          <!-- Recent Activity Timeline -->
          <UCard>
            <template #header>
              <h3 class="font-semibold">Recent Activity</h3>
            </template>
            <UTimeline :items="caseData.timeline.slice(-4).reverse().map(t => ({
              date: new Date(t.date).toLocaleDateString(),
              title: t.event,
              description: t.description,
              icon: 'i-lucide-calendar'
            }))" />
          </UCard>
        </div>

        <!-- Documents Tab -->
        <div v-else-if="activeTab === 'documents'" class="space-y-4">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-bold">Documents ({{ caseData.documents.length }})</h2>
            <UButton label="Upload Document" icon="i-lucide-upload" color="primary" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <UCard v-for="doc in caseData.documents" :key="doc.id" :ui="{ body: 'space-y-3' }">
              <div class="flex items-start gap-3">
                <UIcon :name="documentTypeIcons[doc.type] || 'i-lucide-file'" class="size-8 text-primary" />
                <div class="flex-1 min-w-0">
                  <h3 class="font-medium truncate mb-1">{{ doc.name }}</h3>
                  <p class="text-sm text-dimmed capitalize">{{ doc.type.replace('_', ' ') }}</p>
                </div>
              </div>
              <div class="flex items-center justify-between text-xs text-muted">
                <span>{{ doc.size }}</span>
                <span>{{ new Date(doc.uploadedDate).toLocaleDateString() }}</span>
              </div>
              <div class="flex items-center gap-2">
                <UBadge :label="doc.status" size="sm" variant="soft" class="flex-1 justify-center" />
                <UButton icon="i-lucide-eye" size="sm" color="neutral" variant="outline" />
                <UButton icon="i-lucide-download" size="sm" color="neutral" variant="outline" />
              </div>
            </UCard>
          </div>
        </div>

        <!-- Timeline Tab -->
        <div v-else-if="activeTab === 'timeline'">
          <h2 class="text-2xl font-bold mb-6">Case Timeline</h2>
          <UTimeline
            :items="caseData.timeline.map(t => ({
              date: new Date(t.date).toLocaleDateString(),
              title: t.event,
              description: t.description,
              icon: 'i-lucide-calendar'
            }))"
            color="primary"
          />
        </div>

        <!-- Parties Tab -->
        <div v-else-if="activeTab === 'parties'" class="space-y-4">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-bold">Case Parties ({{ caseData.parties.length }})</h2>
            <UButton label="Add Party" icon="i-lucide-user-plus" color="primary" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <UCard v-for="party in caseData.parties" :key="party.id" :ui="{ body: 'flex items-start gap-4' }">
              <UAvatar :text="party.name[0]" size="lg" />
              <div class="flex-1">
                <h3 class="font-semibold mb-1">{{ party.name }}</h3>
                <p class="text-sm text-muted mb-2">{{ party.role }}</p>
                <div class="flex items-center gap-2 text-sm text-dimmed">
                  <UIcon name="i-lucide-mail" class="size-4" />
                  <span>{{ party.email }}</span>
                </div>
              </div>
            </UCard>
          </div>
        </div>

        <!-- Graph Tab -->
        <div v-else-if="activeTab === 'graph'">
          <h2 class="text-2xl font-bold mb-6">Knowledge Graph</h2>
          <div class="text-center py-20 bg-elevated/30 rounded-lg">
            <UIcon name="i-lucide-network" class="size-20 text-muted mx-auto mb-6 opacity-30" />
            <h3 class="text-xl font-semibold mb-3 text-highlighted">Interactive Knowledge Graph</h3>
            <p class="text-muted mb-6 max-w-md mx-auto">
              Visualize relationships between cases, documents, parties, and entities
            </p>
            <UButton label="Open Full Graph Explorer" icon="i-lucide-expand" color="primary" to="/graph" />
          </div>
        </div>

        <!-- Notes Tab -->
        <div v-else-if="activeTab === 'notes'" class="space-y-4">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-bold">Case Notes</h2>
            <UButton label="Add Note" icon="i-lucide-plus" color="primary" />
          </div>

          <div class="space-y-3">
            <UCard v-for="note in caseData.notes" :key="note.id" :ui="{ body: 'space-y-2' }">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <UAvatar :text="note.author[0]" size="sm" />
                  <span class="font-medium">{{ note.author }}</span>
                </div>
                <span class="text-sm text-dimmed">{{ new Date(note.date).toLocaleDateString() }}</span>
              </div>
              <p class="text-default">{{ note.content }}</p>
            </UCard>
          </div>
        </div>
      </UContainer>
    </div>
  </UDashboardPanel>
</template>
