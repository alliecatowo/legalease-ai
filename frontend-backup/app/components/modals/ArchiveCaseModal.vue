<template>
  <UModal>
    <template #header>
      <h3 class="text-lg font-semibold text-gray-900">Archive Case</h3>
      <p class="text-sm text-gray-600 mt-1">
        Are you sure you want to archive "{{ case?.name }}"?
        This will remove it from active search.
      </p>
    </template>

    <div class="py-4">
      <p class="text-sm text-gray-500">
        Archived cases can be restored later if needed.
        The case data will remain intact.
      </p>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <UButton
          variant="outline"
          @click="emit('close', false)"
        >
          Cancel
        </UButton>
        <UButton
          color="warning"
          @click="emit('close', true)"
        >
          Archive Case
        </UButton>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
interface Props {
  case?: {
    id: string
    name: string
  }
}

defineProps<Props>()

const emit = defineEmits<{
  close: [confirmed: boolean]
}>()
</script>