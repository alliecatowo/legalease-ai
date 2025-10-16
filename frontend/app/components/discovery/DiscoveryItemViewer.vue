<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import type { DiscoveryItem, DiscoveryItemPreview } from '~/types/discovery'

const props = defineProps<{
  item: DiscoveryItem | null
  preview: DiscoveryItemPreview | null
  loading: boolean
  error: string | null
  downloadUrl: string | null
}>()

const hasInlinePreview = computed(() => {
  const type = props.preview?.preview_type
  return [
    'image',
    'video',
    'audio',
    'text',
    'table',
    'key_value',
    'markdown',
    'html'
  ].includes(type as string)
})

const markdownHtml = computed(() => {
  if (!props.preview?.markdown) return ''
  return marked.parse(props.preview.markdown)
})

function sanitizeContent(value: string | null | undefined) {
  if (!value) return ''
  if (typeof window === 'undefined') return value
  return DOMPurify.sanitize(value)
}

function formatBytes(bytes: number) {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / Math.pow(1024, exponent)
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`
}
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="space-y-1">
          <h3 class="font-semibold leading-tight">File Preview</h3>
          <p class="text-xs text-dimmed">
            {{ preview?.content_type || 'Unknown type' }} · {{ formatBytes(preview?.size || item?.item_metadata?.file_size || 0) }}
          </p>
        </div>

        <div class="flex items-center gap-2">
          <UBadge v-if="preview?.preview_type" color="neutral" size="xs" variant="soft">
            {{ preview.preview_type }}
          </UBadge>
          <UButton
            v-if="downloadUrl"
            size="sm"
            color="primary"
            icon="i-lucide-download"
            :href="downloadUrl"
            download
            label="Download"
          />
        </div>
      </div>
    </template>

    <div class="space-y-4">
      <div v-if="loading" class="flex h-48 items-center justify-center">
        <UIcon name="i-lucide-loader-2" class="size-8 animate-spin text-primary" />
      </div>

      <UAlert
        v-else-if="error"
        icon="i-lucide-alert-triangle"
        title="Unable to load preview"
        color="red"
        variant="soft"
      >
        <p class="text-sm text-dimmed">{{ error }}</p>
      </UAlert>

      <div v-else-if="preview && hasInlinePreview" class="space-y-3">
        <div v-if="preview.preview_type === 'image'" class="overflow-hidden rounded-lg border border-default bg-default/40">
          <img
            :src="downloadUrl || undefined"
            :alt="item?.original_filename"
            class="mx-auto max-h-[480px] w-full object-contain"
            loading="lazy"
          />
        </div>

        <div v-else-if="preview.preview_type === 'video'" class="overflow-hidden rounded-lg border border-default bg-default/40 p-2">
          <video
            v-if="downloadUrl"
            :src="downloadUrl"
            controls
            class="mx-auto w-full max-w-3xl rounded-lg bg-black"
          >
            Your browser does not support the video element.
          </video>
        </div>

        <div v-else-if="preview.preview_type === 'audio'" class="rounded-lg border border-default bg-default/40 p-4">
          <audio v-if="downloadUrl" :src="downloadUrl" controls class="w-full">
            Your browser does not support the audio element.
          </audio>
        </div>

        <div v-else-if="preview.preview_type === 'table'" class="overflow-hidden rounded-lg border border-default">
          <div class="max-h-96 w-full overflow-auto">
            <table class="min-w-full divide-y divide-default text-sm">
              <thead class="bg-default/50">
                <tr>
                  <th
                    v-for="(header, index) in preview.headers || []"
                    :key="`${header}-${index}`"
                    class="px-3 py-2 text-left font-semibold uppercase tracking-wide text-xs text-dimmed"
                  >
                    {{ header }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-default bg-surface/40">
                <tr v-for="(row, rowIndex) in preview.rows || []" :key="rowIndex">
                  <td
                    v-for="(value, cellIndex) in row"
                    :key="`${rowIndex}-${cellIndex}`"
                    class="px-3 py-2 font-mono text-xs text-highlighted"
                  >
                    {{ value }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else-if="preview.preview_type === 'key_value'" class="space-y-3">
          <p class="text-xs uppercase font-semibold text-dimmed">Record Details</p>
          <p v-if="(preview.key_values || []).length === 0" class="text-sm text-dimmed">
            No structured details were provided for this file.
          </p>
          <div class="grid gap-3 md:grid-cols-2">
            <div
              v-for="pair in preview.key_values || []"
              :key="pair.label"
              class="rounded-lg border border-default bg-default/40 p-3"
            >
              <p class="text-xs font-semibold uppercase tracking-wide text-dimmed">{{ pair.label }}</p>
              <p class="mt-1 text-sm leading-relaxed text-highlighted whitespace-pre-wrap break-words">{{ pair.value }}</p>
            </div>
          </div>
          <div v-if="preview.text" class="rounded-lg border border-dashed border-default/80 bg-default/20 p-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-dimmed">Raw Data</p>
            <pre class="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-highlighted">{{ preview.text }}</pre>
          </div>
        </div>

        <ClientOnly v-else-if="preview.preview_type === 'markdown'">
          <div class="rounded-lg border border-default bg-default/30 p-4">
            <div class="space-y-2 text-sm leading-relaxed text-highlighted" v-html="sanitizeContent(markdownHtml)" />
          </div>
        </ClientOnly>

        <ClientOnly v-else-if="preview.preview_type === 'html'">
          <div class="rounded-lg border border-default bg-default/30 p-4">
            <div class="space-y-2 text-sm leading-relaxed text-highlighted" v-html="sanitizeContent(preview.html)" />
          </div>
        </ClientOnly>

        <div v-else-if="preview.preview_type === 'text'" class="rounded-lg border border-default bg-default/30 p-4">
          <pre class="max-h-96 overflow-auto text-sm leading-relaxed text-highlighted whitespace-pre-wrap">{{ preview.text }}</pre>
        </div>

        <p v-if="preview.truncated" class="text-xs text-dimmed">
          Preview truncated for large file. Download to view the full content.
        </p>
      </div>

      <div v-else class="space-y-3">
        <UAlert
          icon="i-lucide-eye-off"
          title="Preview not available"
          color="neutral"
          variant="soft"
        >
          <p class="text-sm text-dimmed">
            This file type does not support inline preview. Use the download button to open it with an external application.
          </p>
        </UAlert>

        <UButton
          v-if="downloadUrl"
          color="primary"
          icon="i-lucide-download"
          :href="downloadUrl"
          download
        >
          Download File
        </UButton>
      </div>
    </div>
  </UCard>
</template>
