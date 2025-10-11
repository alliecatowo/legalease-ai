<script setup lang="ts">
const props = defineProps<{
  modelValue: {
    language: string | null
    task: 'transcribe' | 'translate'
    enable_diarization: boolean
    min_speakers: number
    max_speakers: number
    temperature: number
    initial_prompt: string | null
  }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: typeof props.modelValue]
}>()

const showAdvanced = ref(false)

const localValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Common languages for legal transcription
const languageOptions = [
  { value: null, label: 'Auto-detect', icon: 'i-lucide-globe' },
  { value: 'en', label: 'English', icon: 'i-lucide-circle' },
  { value: 'es', label: 'Spanish (Español)', icon: 'i-lucide-circle' },
  { value: 'fr', label: 'French (Français)', icon: 'i-lucide-circle' },
  { value: 'de', label: 'German (Deutsch)', icon: 'i-lucide-circle' },
  { value: 'it', label: 'Italian (Italiano)', icon: 'i-lucide-circle' },
  { value: 'pt', label: 'Portuguese (Português)', icon: 'i-lucide-circle' },
  { value: 'nl', label: 'Dutch (Nederlands)', icon: 'i-lucide-circle' },
  { value: 'pl', label: 'Polish (Polski)', icon: 'i-lucide-circle' },
  { value: 'ru', label: 'Russian (Русский)', icon: 'i-lucide-circle' },
  { value: 'zh', label: 'Chinese (中文)', icon: 'i-lucide-circle' },
  { value: 'ja', label: 'Japanese (日本語)', icon: 'i-lucide-circle' },
  { value: 'ko', label: 'Korean (한국어)', icon: 'i-lucide-circle' },
  { value: 'ar', label: 'Arabic (العربية)', icon: 'i-lucide-circle' },
  { value: 'hi', label: 'Hindi (हिन्दी)', icon: 'i-lucide-circle' },
  { value: 'tr', label: 'Turkish (Türkçe)', icon: 'i-lucide-circle' },
  { value: 'sv', label: 'Swedish (Svenska)', icon: 'i-lucide-circle' },
  { value: 'no', label: 'Norwegian (Norsk)', icon: 'i-lucide-circle' },
  { value: 'da', label: 'Danish (Dansk)', icon: 'i-lucide-circle' },
  { value: 'fi', label: 'Finnish (Suomi)', icon: 'i-lucide-circle' }
]

function updateLanguage(value: string | null) {
  localValue.value = { ...localValue.value, language: value }
}

function updateTask(value: 'transcribe' | 'translate') {
  localValue.value = { ...localValue.value, task: value }
}

function updateDiarization(value: boolean) {
  localValue.value = { ...localValue.value, enable_diarization: value }
}

function updateTemperature(value: number) {
  localValue.value = { ...localValue.value, temperature: value }
}

function updatePrompt(value: string) {
  localValue.value = { ...localValue.value, initial_prompt: value || null }
}

function updateMinSpeakers(value: number) {
  localValue.value = { ...localValue.value, min_speakers: value }
}

function updateMaxSpeakers(value: number) {
  localValue.value = { ...localValue.value, max_speakers: value }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Basic Options -->
    <UCard>
      <template #header>
        <div class="flex items-center gap-3">
          <div class="p-2 bg-primary/10 rounded-lg">
            <UIcon name="i-lucide-settings" class="size-5 text-primary" />
          </div>
          <div>
            <h3 class="font-semibold text-lg">Transcription Options</h3>
            <p class="text-sm text-muted">Configure how your audio will be transcribed</p>
          </div>
        </div>
      </template>

      <div class="space-y-5">
        <!-- Language Selection -->
        <UFormField label="Language" help="Select the language spoken in the audio, or use auto-detect">
          <USelectMenu
            :model-value="modelValue.language"
            :items="languageOptions"
            placeholder="Auto-detect language"
            value-attribute="value"
            @update:model-value="updateLanguage"
          >
            <template #label>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-globe" class="size-4" />
                <span>{{ languageOptions.find(l => l.value === modelValue.language)?.label || 'Auto-detect' }}</span>
              </div>
            </template>
            <template #option="{ option }">
              <div class="flex items-center gap-2">
                <UIcon :name="option.icon" class="size-4" />
                <span>{{ option.label }}</span>
              </div>
            </template>
          </USelectMenu>
        </UFormField>

        <!-- Task Type -->
        <UFormField label="Task" help="Choose to transcribe in the same language or translate to English">
          <URadioGroup
            :model-value="modelValue.task"
            :options="[
              { value: 'transcribe', label: 'Transcribe', description: 'Keep text in original language' },
              { value: 'translate', label: 'Translate to English', description: 'Automatically translate to English' }
            ]"
            @update:model-value="updateTask"
          >
            <template #label="{ option }">
              <div>
                <p class="font-medium">{{ option.label }}</p>
                <p class="text-xs text-muted">{{ option.description }}</p>
              </div>
            </template>
          </URadioGroup>
        </UFormField>

        <!-- Speaker Diarization Toggle -->
        <div class="flex items-start gap-3 p-4 rounded-lg border border-default bg-muted/5">
          <UCheckbox
            :model-value="modelValue.enable_diarization"
            @update:model-value="updateDiarization"
          />
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <UIcon name="i-lucide-users" class="size-4 text-primary" />
              <p class="font-semibold">Speaker Identification</p>
            </div>
            <p class="text-sm text-muted">Automatically detect and label different speakers in the audio</p>
          </div>
        </div>

        <!-- Speaker Count Controls (shown when diarization enabled) -->
        <div v-if="modelValue.enable_diarization" class="space-y-4 p-4 rounded-lg border border-default bg-primary/5">
          <div class="flex items-center gap-2 mb-2">
            <UIcon name="i-lucide-hash" class="size-4 text-primary" />
            <p class="font-semibold">Speaker Count Hints</p>
          </div>
          <p class="text-sm text-muted mb-3">Guide the AI on how many speakers to expect for better accuracy</p>

          <!-- Min Speakers -->
          <UFormField label="Minimum Speakers" :help="`At least ${modelValue.min_speakers} speaker(s) expected`">
            <div class="flex items-center gap-3">
              <input
                type="range"
                :value="modelValue.min_speakers"
                min="1"
                max="20"
                step="1"
                class="flex-1"
                @input="(e) => updateMinSpeakers(parseInt((e.target as HTMLInputElement).value))"
              />
              <UBadge :label="String(modelValue.min_speakers)" color="primary" size="lg" />
            </div>
          </UFormField>

          <!-- Max Speakers -->
          <UFormField label="Maximum Speakers" :help="`Up to ${modelValue.max_speakers} speaker(s) expected`">
            <div class="flex items-center gap-3">
              <input
                type="range"
                :value="modelValue.max_speakers"
                min="1"
                max="20"
                step="1"
                class="flex-1"
                @input="(e) => updateMaxSpeakers(parseInt((e.target as HTMLInputElement).value))"
              />
              <UBadge :label="String(modelValue.max_speakers)" color="primary" size="lg" />
            </div>
          </UFormField>

          <UAlert
            icon="i-lucide-lightbulb"
            color="info"
            variant="soft"
            title="Speaker Count Tips"
            description="For depositions: 2-5 speakers. For hearings/trials: 5-15 speakers. Setting accurate ranges improves diarization quality."
          />
        </div>

        <!-- Advanced Options Toggle -->
        <UButton
          :label="showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'"
          :icon="showAdvanced ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
          color="neutral"
          variant="ghost"
          block
          @click="showAdvanced = !showAdvanced"
        />

        <!-- Advanced Options -->
        <div v-if="showAdvanced" class="space-y-5 pt-4 border-t border-default">
          <!-- Temperature -->
          <UFormField
            label="Temperature"
            :help="`Sampling randomness: ${modelValue.temperature} (0 = deterministic, 1 = creative)`"
          >
            <div class="space-y-2">
              <input
                type="range"
                :value="modelValue.temperature"
                min="0"
                max="1"
                step="0.1"
                class="w-full"
                @input="(e) => updateTemperature(parseFloat((e.target as HTMLInputElement).value))"
              />
              <div class="flex justify-between text-xs text-muted">
                <span>Deterministic</span>
                <span>Balanced</span>
                <span>Creative</span>
              </div>
            </div>
          </UFormField>

          <!-- Initial Prompt -->
          <UFormField
            label="Initial Prompt (Optional)"
            help="Provide context to improve accuracy (e.g., technical terms, names, previous context)"
          >
            <UTextarea
              :model-value="modelValue.initial_prompt || ''"
              placeholder="Example: This is a legal deposition regarding intellectual property dispute..."
              rows="3"
              @update:model-value="updatePrompt"
            />
          </UFormField>

          <UAlert
            icon="i-lucide-info"
            color="info"
            variant="soft"
            title="Advanced Options"
            description="Temperature controls transcription consistency. Use 0 for legal/technical content. Initial prompts help with domain-specific terminology."
          />
        </div>
      </div>
    </UCard>

    <!-- Options Summary -->
    <UCard>
      <template #header>
        <h3 class="font-semibold">Configuration Summary</h3>
      </template>
      <div class="flex flex-wrap gap-2">
        <UBadge :label="`Language: ${languageOptions.find(l => l.value === modelValue.language)?.label || 'Auto'}`" color="primary" variant="soft" />
        <UBadge :label="`Task: ${modelValue.task === 'transcribe' ? 'Transcribe' : 'Translate to English'}`" color="info" variant="soft" />
        <UBadge :label="`Speaker ID: ${modelValue.enable_diarization ? 'Enabled' : 'Disabled'}`" :color="modelValue.enable_diarization ? 'success' : 'neutral'" variant="soft" />
        <UBadge v-if="modelValue.enable_diarization" :label="`Speakers: ${modelValue.min_speakers}-${modelValue.max_speakers}`" color="success" variant="soft" />
        <UBadge v-if="modelValue.temperature > 0" :label="`Temperature: ${modelValue.temperature}`" color="warning" variant="soft" />
        <UBadge v-if="modelValue.initial_prompt" label="Custom Prompt" color="secondary" variant="soft" />
      </div>
    </UCard>
  </div>
</template>
