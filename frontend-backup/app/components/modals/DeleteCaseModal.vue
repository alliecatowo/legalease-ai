<template>
  <UModal>
    <template #header>
      <h3 class="text-lg font-semibold text-red-600">Delete Case</h3>
      <p class="text-sm text-gray-600 mt-1">
        Are you sure you want to permanently delete "{{ case?.name }}"?
      </p>
    </template>

    <div class="py-4">
      <div class="bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex">
          <UIcon name="i-heroicons-exclamation-triangle-20-solid" class="w-5 h-5 text-red-400" />
          <div class="ml-3">
            <h4 class="text-sm font-medium text-red-800">Warning</h4>
            <p class="text-sm text-red-700 mt-1">
              This action cannot be undone. All documents and data associated with this case will be permanently removed.
            </p>
          </div>
        </div>
      </div>
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
          color="error"
          @click="emit('close', true)"
        >
          Delete Case
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