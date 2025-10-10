<script setup lang="ts">
import type { Case } from '~/composables/useCaseManagement'

const props = defineProps<{
  case: Case
}>()

const emit = defineEmits<{
  'update-status': [status: Case['status']]
  'edit': []
  'archive': []
  'share': []
}>()

const statusColors: Record<Case['status'], string> = {
  active: 'success',
  pending: 'warning',
  closed: 'neutral',
  archived: 'error'
}

const statusOptions = [
  { label: 'Active', value: 'active' },
  { label: 'Pending', value: 'pending' },
  { label: 'Closed', value: 'closed' },
  { label: 'Archived', value: 'archived' }
]
</script>

<template>
  <div class="bg-default border-b border-default">
    <div class="p-6">
      <div class="flex items-start justify-between mb-4">
        <div class="flex-1">
          <div class="flex items-center gap-3 mb-2">
            <h1 class="text-2xl font-bold text-highlighted">
              {{ case.title }}
            </h1>
            <UBadge
              :label="case.status"
              :color="statusColors[case.status]"
              variant="soft"
              size="md"
            />
          </div>
          <p class="text-muted mb-2">
            {{ case.caseNumber }} • {{ case.jurisdiction }}
          </p>
          <p v-if="case.description" class="text-default max-w-3xl">
            {{ case.description }}
          </p>
        </div>

        <div class="flex items-center gap-2">
          <UButton
            label="Edit"
            icon="i-lucide-edit"
            color="neutral"
            variant="outline"
            @click="emit('edit')"
          />
          <UButton
            label="Share"
            icon="i-lucide-share"
            color="neutral"
            variant="outline"
            @click="emit('share')"
          />
          <UDropdownMenu
            :items="[
              [
                { label: 'Archive Case', icon: 'i-lucide-archive', click: () => emit('archive') },
                { label: 'Export PDF', icon: 'i-lucide-download' },
                { label: 'Print', icon: 'i-lucide-printer' }
              ]
            ]"
          >
            <UButton
              icon="i-lucide-more-horizontal"
              color="neutral"
              variant="outline"
            />
          </UDropdownMenu>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="grid grid-cols-4 gap-4">
        <div class="p-4 rounded-lg bg-muted/20">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-users" class="size-8 text-primary" />
            <div>
              <p class="text-2xl font-bold text-highlighted">{{ case.parties.length }}</p>
              <p class="text-sm text-muted">Parties</p>
            </div>
          </div>
        </div>

        <div class="p-4 rounded-lg bg-muted/20">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-file-text" class="size-8 text-primary" />
            <div>
              <p class="text-2xl font-bold text-highlighted">{{ case.documents.length }}</p>
              <p class="text-sm text-muted">Documents</p>
            </div>
          </div>
        </div>

        <div class="p-4 rounded-lg bg-muted/20">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-calendar" class="size-8 text-primary" />
            <div>
              <p class="text-2xl font-bold text-highlighted">
                {{ case.deadlines.filter(d => !d.completed).length }}
              </p>
              <p class="text-sm text-muted">Upcoming Deadlines</p>
            </div>
          </div>
        </div>

        <div class="p-4 rounded-lg bg-muted/20">
          <div class="flex items-center gap-3">
            <UIcon name="i-lucide-check-circle" class="size-8 text-primary" />
            <div>
              <p class="text-2xl font-bold text-highlighted">
                {{ case.tasks.filter(t => !t.completed).length }}
              </p>
              <p class="text-sm text-muted">Tasks Remaining</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
