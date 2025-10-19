<script setup lang="ts">
import { ref } from 'vue'
import { today, getLocalTimeZone, type DateValue } from '@internationalized/date'

const open = defineModel<boolean>('open')
const emit = defineEmits<{
  'created': [caseData: any]
}>()

// Stepper state
const currentStep = ref(0)

// Form data
const caseData = ref({
  name: '',
  caseNumber: '',
  caseType: '',
  jurisdiction: '',
  court: '',
  description: '',
  tags: [] as string[],
  parties: [] as Array<{ name: string; role: string; type: 'plaintiff' | 'defendant' | 'witness' | 'other' }>,
  documents: [] as File[],
  timeline: [] as Array<{ date: DateValue; event: string; description: string }>,
  analysisTypes: [] as string[]
})

const caseTypes = [
  { label: 'Civil Litigation', value: 'civil' },
  { label: 'Corporate', value: 'corporate' },
  { label: 'Patent', value: 'patent' },
  { label: 'Employment', value: 'employment' },
  { label: 'Real Estate', value: 'real_estate' },
  { label: 'Criminal', value: 'criminal' },
  { label: 'Family Law', value: 'family' },
  { label: 'Other', value: 'other' }
]

const jurisdictions = [
  { label: 'Federal', value: 'federal' },
  { label: 'California', value: 'ca' },
  { label: 'New York', value: 'ny' },
  { label: 'Texas', value: 'tx' },
  { label: 'Delaware', value: 'de' },
  { label: 'Other', value: 'other' }
]

const partyRoles = [
  { label: 'Plaintiff', value: 'plaintiff' },
  { label: 'Defendant', value: 'defendant' },
  { label: 'Witness', value: 'witness' },
  { label: 'Expert', value: 'expert' },
  { label: 'Other', value: 'other' }
]

const analysisOptions = [
  { label: 'Entity Extraction', value: 'entities', description: 'Extract people, organizations, dates, amounts' },
  { label: 'Clause Analysis', value: 'clauses', description: 'Identify and analyze legal clauses' },
  { label: 'Document Similarity', value: 'similarity', description: 'Find similar documents' },
  { label: 'Timeline Generation', value: 'timeline', description: 'Auto-generate case timeline' },
  { label: 'Risk Assessment', value: 'risk', description: 'Identify potential risks and issues' }
]

const steps = [
  { title: 'Basic Info', description: 'Case details', icon: 'i-lucide-info' },
  { title: 'Parties', description: 'Add parties', icon: 'i-lucide-users' },
  { title: 'Documents', description: 'Attach documents', icon: 'i-lucide-files' },
  // { title: 'Timeline', description: 'Key dates', icon: 'i-lucide-calendar' },
  { title: 'Analysis', description: 'AI processing', icon: 'i-lucide-sparkles' }
]

const newParty = ref({ name: '', role: 'plaintiff', type: 'plaintiff' as const })
const newEvent = ref({ date: today(getLocalTimeZone()), event: '', description: '' })

function addParty() {
  if (newParty.value.name.trim()) {
    caseData.value.parties.push({ ...newParty.value })
    newParty.value = { name: '', role: 'plaintiff', type: 'plaintiff' }
  }
}

function removeParty(index: number) {
  caseData.value.parties.splice(index, 1)
}

function addEvent() {
  if (newEvent.value.event.trim()) {
    caseData.value.timeline.push({ ...newEvent.value })
    newEvent.value = { date: today(getLocalTimeZone()), event: '', description: '' }
  }
}

function removeEvent(index: number) {
  caseData.value.timeline.splice(index, 1)
}

function nextStep() {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function canProceed() {
  switch (currentStep.value) {
    case 0:
      return caseData.value.name && caseData.value.caseNumber && caseData.value.caseType
    case 1:
      return caseData.value.parties.length > 0
    case 2:
      return true // Documents optional
    case 3:
      return true // Analysis optional
    default:
      return false
  }
}

const isCreating = ref(false)

async function createCase() {
  if (isCreating.value) return

  try {
    isCreating.value = true
    const api = useApi()
    const toast = useToast()

    // Map frontend data to backend schema
    const payload = {
      name: caseData.value.name,
      case_number: caseData.value.caseNumber,
      client: caseData.value.parties[0]?.name || 'Unknown Client',
      matter_type: caseData.value.caseType
    }

    const result = await api.cases.create(payload)

    toast.add({
      title: 'Success',
      description: `Case "${result.name}" created successfully`,
      color: 'success'
    })

    emit('created', result)
    open.value = false
    resetForm()
  } catch (error: any) {
    const toast = useToast()
    toast.add({
      title: 'Error',
      description: error.message || 'Failed to create case',
      color: 'error'
    })
  } finally {
    isCreating.value = false
  }
}

function resetForm() {
  currentStep.value = 0
  caseData.value = {
    name: '',
    caseNumber: '',
    caseType: '',
    jurisdiction: '',
    court: '',
    description: '',
    tags: [],
    parties: [],
    documents: [],
    timeline: [],
    analysisTypes: []
  }
}
</script>

<template>
  <UModal v-model:open="open" :ui="{ content: 'max-w-4xl', body: 'p-0' }">
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-lucide-folder-plus" class="size-6 text-primary" />
        <div>
          <h2 class="text-xl font-semibold">Create New Case</h2>
          <p class="text-sm text-muted mt-0.5">{{ steps[currentStep].description }}</p>
        </div>
      </div>
    </template>

    <template #body>
      <!-- Stepper Header -->
      <div class="border-b border-default px-6 py-4">
        <UStepper :model-value="currentStep" :items="steps" size="sm" />
      </div>

      <!-- Step Content -->
      <div class="p-6 min-h-[400px]">
        <!-- Step 1: Basic Info -->
        <div v-if="currentStep === 0" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <UFormField label="Case Name" name="name" required>
              <UInput v-model="caseData.name" placeholder="e.g., Acme Corp v. Global Tech" />
            </UFormField>
            <UFormField label="Case Number" name="caseNumber" required>
              <UInput v-model="caseData.caseNumber" placeholder="e.g., 2024-CV-12345" />
            </UFormField>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <UFormField label="Case Type" name="caseType" required>
              <USelect v-model="caseData.caseType" :items="caseTypes" placeholder="Select type" />
            </UFormField>
            <UFormField label="Jurisdiction" name="jurisdiction">
              <USelect v-model="caseData.jurisdiction" :items="jurisdictions" placeholder="Select jurisdiction" />
            </UFormField>
          </div>

          <UFormField label="Court" name="court">
            <UInput v-model="caseData.court" placeholder="e.g., Superior Court of California" />
          </UFormField>

          <UFormField label="Description" name="description">
            <UTextarea v-model="caseData.description" placeholder="Brief case description..." :rows="3" />
          </UFormField>

          <UFormField label="Tags" name="tags">
            <UInputTags v-model="caseData.tags" placeholder="Add tags..." />
          </UFormField>
        </div>

        <!-- Step 2: Parties -->
        <div v-if="currentStep === 1" class="space-y-4">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-medium">Case Parties</h3>
            <UBadge :label="`${caseData.parties.length} parties`" variant="soft" />
          </div>

          <!-- Add Party Form -->
          <UCard :ui="{ body: 'space-y-3' }">
            <h4 class="text-sm font-medium mb-3">Add Party</h4>
            <div class="grid grid-cols-3 gap-3">
              <UInput v-model="newParty.name" placeholder="Party name" class="col-span-2" />
              <USelect v-model="newParty.role" :items="partyRoles" />
            </div>
            <UButton label="Add Party" icon="i-lucide-plus" size="sm" @click="addParty" block />
          </UCard>

          <!-- Parties List -->
          <div v-if="caseData.parties.length" class="space-y-2">
            <UCard v-for="(party, idx) in caseData.parties" :key="idx" :ui="{ body: 'p-3' }">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <UAvatar :text="party.name[0]" size="sm" />
                  <div>
                    <p class="font-medium">{{ party.name }}</p>
                    <p class="text-sm text-muted capitalize">{{ party.role }}</p>
                  </div>
                </div>
                <UButton icon="i-lucide-trash-2" color="error" variant="ghost" size="sm" @click="removeParty(idx)" />
              </div>
            </UCard>
          </div>

          <div v-else class="text-center py-8">
            <UIcon name="i-lucide-users-round" class="size-12 text-muted mx-auto mb-3 opacity-50" />
            <p class="text-sm text-muted">No parties added yet</p>
          </div>
        </div>

        <!-- Step 3: Documents -->
        <div v-if="currentStep === 2" class="space-y-4">
          <UFileUpload v-model="caseData.documents" multiple accept=".pdf,.doc,.docx" class="w-full">
            <template #default="{ attrs, open }">
              <div class="text-center py-12 cursor-pointer" v-bind="attrs" @click="open">
                <UIcon name="i-lucide-upload" class="size-12 text-primary mx-auto mb-4" />
                <h3 class="font-medium mb-2">Upload Documents</h3>
                <p class="text-sm text-muted mb-4">Drag and drop files or click to browse</p>
                <UButton label="Browse Files" color="primary" type="button" />
              </div>
            </template>
          </UFileUpload>

          <div v-if="caseData.documents.length" class="space-y-2">
            <UCard v-for="(file, idx) in caseData.documents" :key="idx" :ui="{ body: 'p-3' }">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <UIcon name="i-lucide-file-text" class="size-5 text-muted" />
                  <div>
                    <p class="font-medium text-sm">{{ file.name }}</p>
                    <p class="text-xs text-muted">{{ (file.size / 1024).toFixed(1) }} KB</p>
                  </div>
                </div>
                <UButton
                  icon="i-lucide-x"
                  color="error"
                  variant="ghost"
                  size="sm"
                  @click="caseData.documents.splice(idx, 1)"
                />
              </div>
            </UCard>
          </div>

          <p class="text-sm text-dimmed text-center">
            Supported formats: PDF, Word (.doc, .docx)
          </p>
        </div>

        <!-- Step 4: Analysis -->
        <div v-if="currentStep === 3" class="space-y-4">
          <div class="mb-4">
            <h3 class="font-medium mb-2">AI Analysis Options</h3>
            <p class="text-sm text-muted">Select the types of analysis to run on your case documents</p>
          </div>

          <UCheckboxGroup v-model="caseData.analysisTypes" class="space-y-3">
            <UCard v-for="option in analysisOptions" :key="option.value" :ui="{ body: 'p-4' }">
              <div class="flex items-start gap-3">
                <UCheckbox :value="option.value" class="mt-1" />
                <div class="flex-1">
                  <p class="font-medium">{{ option.label }}</p>
                  <p class="text-sm text-muted mt-1">{{ option.description }}</p>
                </div>
              </div>
            </UCard>
          </UCheckboxGroup>

          <UAlert
            icon="i-lucide-info"
            color="info"
            variant="soft"
            title="Processing Time"
            description="AI analysis will run in the background. You'll be notified when complete."
          />
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex items-center justify-between">
        <UButton
          v-if="currentStep > 0"
          label="Back"
          icon="i-lucide-arrow-left"
          color="neutral"
          variant="outline"
          @click="prevStep"
        />
        <div v-else />

        <div class="flex items-center gap-2">
          <UButton label="Cancel" color="neutral" variant="ghost" @click="open = false" />
          <UButton
            v-if="currentStep < steps.length - 1"
            label="Next"
            trailing-icon="i-lucide-arrow-right"
            color="primary"
            :disabled="!canProceed()"
            @click="nextStep"
          />
          <UButton
            v-else
            :label="isCreating ? 'Creating...' : 'Create Case'"
            :icon="isCreating ? 'i-lucide-loader-2' : 'i-lucide-check'"
            :loading="isCreating"
            :disabled="isCreating"
            color="primary"
            @click="createCase"
          />
        </div>
      </div>
    </template>
  </UModal>
</template>
