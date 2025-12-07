<script setup lang="ts">
import { ref } from 'vue'
import type { Speaker } from '~/composables/useTranscription'

const props = defineProps<{
  speakers: Speaker[]
  selectedSpeaker?: string | null
}>()

const emit = defineEmits<{
  'select-speaker': [speakerId: string | null]
  'add-speaker': [name: string, role?: string]
  'update-speaker': [speakerId: string, updates: Partial<Speaker>]
  'delete-speaker': [speakerId: string]
}>()

const showAddSpeakerModal = ref(false)
const newSpeakerName = ref('')
const newSpeakerRole = ref('')
const editingSpeaker = ref<Speaker | null>(null)

// Add new speaker
function handleAddSpeaker() {
  if (!newSpeakerName.value.trim()) return

  emit('add-speaker', newSpeakerName.value, newSpeakerRole.value || undefined)
  newSpeakerName.value = ''
  newSpeakerRole.value = ''
  showAddSpeakerModal.value = false
}

// Start editing speaker
function startEdit(speaker: Speaker) {
  editingSpeaker.value = { ...speaker }
}

// Save speaker edits
function saveEdit() {
  if (!editingSpeaker.value) return

  emit('update-speaker', editingSpeaker.value.id, {
    name: editingSpeaker.value.name,
    role: editingSpeaker.value.role
  })
  editingSpeaker.value = null
}

// Cancel edit
function cancelEdit() {
  editingSpeaker.value = null
}

// Delete speaker
function handleDelete(speakerId: string) {
  if (confirm('Are you sure you want to delete this speaker?')) {
    emit('delete-speaker', speakerId)
  }
}

// Toggle speaker filter
function toggleSpeaker(speakerId: string) {
  if (props.selectedSpeaker === speakerId) {
    emit('select-speaker', null)
  } else {
    emit('select-speaker', speakerId)
  }
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="p-4 border-b border-default">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-users" class="size-5 text-primary" />
          <h3 class="font-semibold text-highlighted">
            Speakers
          </h3>
          <UBadge :label="String(speakers.length)" size="sm" variant="soft" />
        </div>
        <UButton
          icon="i-lucide-plus"
          color="primary"
          size="xs"
          @click="showAddSpeakerModal = true"
        />
      </div>
      <p class="text-xs text-muted">
        Click to filter by speaker
      </p>
    </div>

    <!-- Speaker List -->
    <div class="flex-1 overflow-y-auto p-4 space-y-2">
      <div
        v-for="speaker in speakers"
        :key="speaker.id"
        class="p-3 rounded-lg transition-all cursor-pointer"
        :class="[
          selectedSpeaker === speaker.id
            ? 'bg-primary/10 ring-1 ring-primary'
            : 'bg-muted/10 hover:bg-muted/20'
        ]"
        @click="toggleSpeaker(speaker.id)"
      >
        <div v-if="editingSpeaker?.id === speaker.id" class="space-y-2">
          <UInput
            v-model="editingSpeaker.name"
            placeholder="Speaker name"
            size="sm"
          />
          <UInput
            v-model="editingSpeaker.role"
            placeholder="Role (optional)"
            size="sm"
          />
          <div class="flex gap-2">
            <UButton
              label="Save"
              icon="i-lucide-check"
              color="primary"
              size="xs"
              @click.stop="saveEdit"
            />
            <UButton
              label="Cancel"
              icon="i-lucide-x"
              color="neutral"
              variant="ghost"
              size="xs"
              @click.stop="cancelEdit"
            />
          </div>
        </div>

        <div v-else class="flex items-start justify-between gap-2">
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <!-- Color indicator -->
            <div
              class="w-3 h-3 rounded-full shrink-0"
              :style="{ backgroundColor: speaker.color }"
            />

            <!-- Speaker info -->
            <div class="flex-1 min-w-0">
              <p class="font-medium text-highlighted truncate">
                {{ speaker.name }}
              </p>
              <p v-if="speaker.role" class="text-xs text-muted truncate">
                {{ speaker.role }}
              </p>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1" @click.stop>
            <UTooltip text="Edit Speaker">
              <UButton
                icon="i-lucide-edit"
                color="neutral"
                variant="ghost"
                size="xs"
                @click="startEdit(speaker)"
              />
            </UTooltip>
            <UTooltip text="Delete Speaker">
              <UButton
                icon="i-lucide-trash"
                color="error"
                variant="ghost"
                size="xs"
                @click="handleDelete(speaker.id)"
              />
            </UTooltip>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="speakers.length === 0" class="text-center py-12">
        <UIcon name="i-lucide-users" class="size-12 text-muted mx-auto mb-4 opacity-30" />
        <p class="text-sm text-muted mb-4">
          No speakers added yet
        </p>
        <UButton
          label="Add First Speaker"
          icon="i-lucide-plus"
          color="primary"
          size="sm"
          @click="showAddSpeakerModal = true"
        />
      </div>
    </div>

    <!-- Add Speaker Modal -->
    <UModal v-model:open="showAddSpeakerModal">
      <template #header>
        <h3 class="font-semibold text-highlighted">
          Add Speaker
        </h3>
      </template>

      <template #body>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-muted mb-2">Name *</label>
            <UInput
              v-model="newSpeakerName"
              placeholder="Enter speaker name"
              autofocus
              @keydown.enter="handleAddSpeaker"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-muted mb-2">Role (Optional)</label>
            <UInput
              v-model="newSpeakerRole"
              placeholder="e.g., Attorney, Witness, Expert"
              @keydown.enter="handleAddSpeaker"
            />
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showAddSpeakerModal = false"
          />
          <UButton
            label="Add Speaker"
            icon="i-lucide-plus"
            color="primary"
            :disabled="!newSpeakerName.trim()"
            @click="handleAddSpeaker"
          />
        </div>
      </template>
    </UModal>
  </div>
</template>
