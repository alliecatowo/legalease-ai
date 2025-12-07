<script setup lang="ts">
import { ref } from 'vue'

const toast = useToast()

// Preferences state
const preferences = reactive({
  // General
  theme: 'system',
  language: 'en',
  timezone: 'America/New_York',

  // Document Processing
  autoOCR: true,
  autoEntityExtraction: true,
  autoSummarization: false,
  defaultDocumentType: 'general',

  // Search
  searchResultsPerPage: 25,
  enableSemanticSearch: true,
  enableFuzzySearch: true,
  searchHistoryEnabled: true,

  // Notifications
  emailNotifications: true,
  caseUpdates: true,
  documentProcessing: false,
  weeklyDigest: true,

  // AI & Processing
  aiModel: 'gpt-4',
  maxTokens: 2048,
  temperature: 0.7,
  enableSpeakerDiarization: true,

  // Privacy
  dataRetention: 365,
  shareUsageData: false,
  enableTelemetry: true
})

const themeOptions = [
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' },
  { label: 'System', value: 'system' }
]

const languageOptions = [
  { label: 'English', value: 'en' },
  { label: 'Spanish', value: 'es' },
  { label: 'French', value: 'fr' }
]

const timezoneOptions = [
  { label: 'Eastern Time (ET)', value: 'America/New_York' },
  { label: 'Central Time (CT)', value: 'America/Chicago' },
  { label: 'Mountain Time (MT)', value: 'America/Denver' },
  { label: 'Pacific Time (PT)', value: 'America/Los_Angeles' }
]

const documentTypeOptions = [
  { label: 'General', value: 'general' },
  { label: 'Contract', value: 'contract' },
  { label: 'Agreement', value: 'agreement' },
  { label: 'Court Filing', value: 'court_filing' },
  { label: 'Transcript', value: 'transcript' }
]

const resultsPerPageOptions = [
  { label: '10', value: 10 },
  { label: '25', value: 25 },
  { label: '50', value: 50 },
  { label: '100', value: 100 }
]

const aiModelOptions = [
  { label: 'GPT-4', value: 'gpt-4' },
  { label: 'GPT-3.5', value: 'gpt-3.5-turbo' },
  { label: 'Claude 3', value: 'claude-3' }
]

const dataRetentionOptions = [
  { label: '30 Days', value: 30 },
  { label: '90 Days', value: 90 },
  { label: '1 Year', value: 365 },
  { label: '2 Years', value: 730 },
  { label: 'Forever', value: -1 }
]

async function savePreferences() {
  // TODO: Save to backend
  toast.add({
    title: 'Success',
    description: 'Preferences saved successfully',
    icon: 'i-lucide-check',
    color: 'success'
  })
}

function resetToDefaults() {
  if (confirm('Reset all preferences to default values?')) {
    // Reset to defaults
    preferences.theme = 'system'
    preferences.language = 'en'
    preferences.autoOCR = true
    preferences.autoEntityExtraction = true
    // ... reset all others

    toast.add({
      title: 'Reset',
      description: 'Preferences reset to defaults',
      icon: 'i-lucide-rotate-ccw',
      color: 'neutral'
    })
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <UPageCard
      title="Preferences"
      description="Customize how LegalEase works for you"
      variant="naked"
      orientation="horizontal"
      class="mb-4"
    >
      <div class="flex items-center gap-2 lg:ms-auto">
        <UButton
          label="Reset to Defaults"
          icon="i-lucide-rotate-ccw"
          color="neutral"
          variant="ghost"
          @click="resetToDefaults"
        />
        <UButton
          label="Save Changes"
          icon="i-lucide-save"
          color="primary"
          @click="savePreferences"
        />
      </div>
    </UPageCard>

    <!-- General Settings -->
    <UPageCard title="General" variant="subtle">
      <UFormField
        label="Theme"
        description="Choose your preferred color scheme"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.theme" :items="themeOptions" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Language"
        description="Select your preferred language"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.language" :items="languageOptions" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Timezone"
        description="Your local timezone for dates and times"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.timezone" :items="timezoneOptions" />
      </UFormField>
    </UPageCard>

    <!-- Document Processing -->
    <UPageCard title="Document Processing" variant="subtle">
      <UFormField
        label="Auto OCR"
        description="Automatically extract text from scanned documents"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.autoOCR" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Auto Entity Extraction"
        description="Automatically identify people, organizations, dates, etc."
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.autoEntityExtraction" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Auto Summarization"
        description="Generate AI summaries for uploaded documents"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.autoSummarization" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Default Document Type"
        description="Pre-selected type for new documents"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.defaultDocumentType" :items="documentTypeOptions" />
      </UFormField>
    </UPageCard>

    <!-- Search Preferences -->
    <UPageCard title="Search" variant="subtle">
      <UFormField
        label="Results Per Page"
        description="Number of search results to show per page"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.searchResultsPerPage" :items="resultsPerPageOptions" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Semantic Search"
        description="Enable AI-powered semantic search for better results"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.enableSemanticSearch" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Fuzzy Search"
        description="Allow approximate matches for misspellings"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.enableFuzzySearch" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Search History"
        description="Save your search queries for quick access"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.searchHistoryEnabled" />
      </UFormField>
    </UPageCard>

    <!-- AI Settings -->
    <UPageCard title="AI & Processing" variant="subtle">
      <UFormField
        label="AI Model"
        description="Select the AI model for processing tasks"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.aiModel" :items="aiModelOptions" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Max Tokens"
        description="Maximum tokens for AI responses (higher = longer responses)"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <div class="space-y-2 w-full max-w-xs">
          <input
            v-model.number="preferences.maxTokens"
            type="range"
            min="512"
            max="8192"
            step="256"
            class="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
          >
          <div class="flex justify-between text-xs text-muted">
            <span>512</span>
            <span class="font-medium text-highlighted">{{ preferences.maxTokens }}</span>
            <span>8192</span>
          </div>
        </div>
      </UFormField>

      <USeparator />

      <UFormField
        label="Temperature"
        description="Creativity level (lower = more focused, higher = more creative)"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <div class="space-y-2 w-full max-w-xs">
          <input
            v-model.number="preferences.temperature"
            type="range"
            min="0"
            max="1"
            step="0.1"
            class="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
          >
          <div class="flex justify-between text-xs text-muted">
            <span>0.0 (Focused)</span>
            <span class="font-medium text-highlighted">{{ preferences.temperature.toFixed(1) }}</span>
            <span>1.0 (Creative)</span>
          </div>
        </div>
      </UFormField>

      <USeparator />

      <UFormField
        label="Speaker Diarization"
        description="Automatically identify different speakers in transcriptions"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.enableSpeakerDiarization" />
      </UFormField>
    </UPageCard>

    <!-- Notifications -->
    <UPageCard title="Notifications" variant="subtle">
      <UFormField
        label="Email Notifications"
        description="Receive notifications via email"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.emailNotifications" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Case Updates"
        description="Notify when cases are updated"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.caseUpdates" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Document Processing"
        description="Notify when document processing completes"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.documentProcessing" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Weekly Digest"
        description="Receive a weekly summary of activity"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.weeklyDigest" />
      </UFormField>
    </UPageCard>

    <!-- Privacy & Data -->
    <UPageCard title="Privacy & Data" variant="subtle">
      <UFormField
        label="Data Retention"
        description="How long to keep your data"
        class="flex max-sm:flex-col justify-between items-start gap-4"
      >
        <USelectMenu v-model="preferences.dataRetention" :items="dataRetentionOptions" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Share Usage Data"
        description="Help improve LegalEase by sharing anonymous usage data"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.shareUsageData" />
      </UFormField>

      <USeparator />

      <UFormField
        label="Enable Telemetry"
        description="Send diagnostic data to help us fix issues"
        class="flex max-sm:flex-col justify-between sm:items-center gap-4"
      >
        <UToggle v-model="preferences.enableTelemetry" />
      </UFormField>
    </UPageCard>
  </div>
</template>
