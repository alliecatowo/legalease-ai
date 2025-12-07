<script setup lang="ts">
import { ref } from 'vue'

const toast = useToast()

// API Keys
const apiKeys = ref([
  {
    id: '1',
    name: 'Production API Key',
    key: 'sk_live_...abc123',
    created: '2024-01-15',
    lastUsed: '2024-03-10',
    permissions: ['read', 'write']
  },
  {
    id: '2',
    name: 'Development API Key',
    key: 'sk_test_...xyz789',
    created: '2024-02-01',
    lastUsed: '2024-03-09',
    permissions: ['read']
  }
])

// Integrations
const integrations = ref([
  {
    id: 'dropbox',
    name: 'Dropbox',
    icon: 'i-lucide-cloud',
    description: 'Sync documents with Dropbox',
    enabled: true,
    configured: true
  },
  {
    id: 'google-drive',
    name: 'Google Drive',
    icon: 'i-lucide-hard-drive',
    description: 'Sync documents with Google Drive',
    enabled: false,
    configured: false
  },
  {
    id: 'slack',
    name: 'Slack',
    icon: 'i-lucide-message-square',
    description: 'Send notifications to Slack',
    enabled: true,
    configured: true
  },
  {
    id: 'microsoft-teams',
    name: 'Microsoft Teams',
    icon: 'i-lucide-users',
    description: 'Send notifications to Microsoft Teams',
    enabled: false,
    configured: false
  },
  {
    id: 'zapier',
    name: 'Zapier',
    icon: 'i-lucide-zap',
    description: 'Connect with 5000+ apps via Zapier',
    enabled: false,
    configured: false
  }
])

// Webhooks
const webhooks = ref([
  {
    id: '1',
    url: 'https://example.com/webhooks/legalease',
    events: ['document.uploaded', 'case.updated'],
    enabled: true,
    lastTriggered: '2024-03-10 14:32'
  }
])

const showNewKeyModal = ref(false)
const showNewWebhookModal = ref(false)
const newKeyName = ref('')
const newKeyPermissions = ref<string[]>([])
const newWebhookUrl = ref('')
const newWebhookEvents = ref<string[]>([])

const permissionOptions = [
  { label: 'Read', value: 'read' },
  { label: 'Write', value: 'write' },
  { label: 'Delete', value: 'delete' }
]

const eventOptions = [
  { label: 'Document Uploaded', value: 'document.uploaded' },
  { label: 'Document Processed', value: 'document.processed' },
  { label: 'Case Created', value: 'case.created' },
  { label: 'Case Updated', value: 'case.updated' },
  { label: 'Search Performed', value: 'search.performed' }
]

function createAPIKey() {
  const newKey = {
    id: String(apiKeys.value.length + 1),
    name: newKeyName.value,
    key: 'sk_live_' + Math.random().toString(36).substring(7),
    created: new Date().toISOString().split('T')[0],
    lastUsed: null,
    permissions: newKeyPermissions.value
  }

  apiKeys.value.push(newKey)
  showNewKeyModal.value = false
  newKeyName.value = ''
  newKeyPermissions.value = []

  toast.add({
    title: 'API Key Created',
    description: `Copy your new API key: ${newKey.key}`,
    icon: 'i-lucide-key',
    color: 'success'
  })
}

function deleteAPIKey(id: string) {
  if (confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
    apiKeys.value = apiKeys.value.filter(k => k.id !== id)
    toast.add({
      title: 'API Key Deleted',
      icon: 'i-lucide-trash',
      color: 'neutral'
    })
  }
}

function toggleIntegration(integrationId: string) {
  const integration = integrations.value.find(i => i.id === integrationId)
  if (integration) {
    integration.enabled = !integration.enabled
    toast.add({
      title: integration.enabled ? 'Integration Enabled' : 'Integration Disabled',
      description: integration.name,
      icon: integration.enabled ? 'i-lucide-check' : 'i-lucide-x',
      color: integration.enabled ? 'success' : 'neutral'
    })
  }
}

function configureIntegration(integrationId: string) {
  // TODO: Open configuration modal
  toast.add({
    title: 'Configuration',
    description: 'Integration configuration coming soon',
    icon: 'i-lucide-settings',
    color: 'neutral'
  })
}

function createWebhook() {
  const newWebhook = {
    id: String(webhooks.value.length + 1),
    url: newWebhookUrl.value,
    events: newWebhookEvents.value,
    enabled: true,
    lastTriggered: null
  }

  webhooks.value.push(newWebhook)
  showNewWebhookModal.value = false
  newWebhookUrl.value = ''
  newWebhookEvents.value = []

  toast.add({
    title: 'Webhook Created',
    icon: 'i-lucide-webhook',
    color: 'success'
  })
}

function deleteWebhook(id: string) {
  if (confirm('Delete this webhook?')) {
    webhooks.value = webhooks.value.filter(w => w.id !== id)
    toast.add({
      title: 'Webhook Deleted',
      icon: 'i-lucide-trash',
      color: 'neutral'
    })
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  toast.add({
    title: 'Copied to clipboard',
    icon: 'i-lucide-copy',
    color: 'neutral'
  })
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <UPageCard
      title="API & Integrations"
      description="Manage API keys, webhooks, and third-party integrations"
      variant="naked"
      orientation="horizontal"
    />

    <!-- API Keys -->
    <UPageCard title="API Keys" variant="subtle">
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-muted">
            Use API keys to authenticate requests to the LegalEase API
          </p>
          <UButton
            label="Create New Key"
            icon="i-lucide-plus"
            color="primary"
            size="sm"
            @click="showNewKeyModal = true"
          />
        </div>

        <div class="space-y-3">
          <UCard
            v-for="key in apiKeys"
            :key="key.id"
            class="bg-muted/10"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 space-y-2">
                <div class="flex items-center gap-2">
                  <h4 class="font-semibold text-highlighted">
                    {{ key.name }}
                  </h4>
                  <UBadge
                    v-for="perm in key.permissions"
                    :key="perm"
                    :label="perm"
                    size="xs"
                    variant="subtle"
                  />
                </div>
                <div class="flex items-center gap-2">
                  <code class="text-xs bg-muted px-2 py-1 rounded">{{ key.key }}</code>
                  <UButton
                    icon="i-lucide-copy"
                    color="neutral"
                    variant="ghost"
                    size="xs"
                    @click="copyToClipboard(key.key)"
                  />
                </div>
                <div class="text-xs text-muted">
                  Created {{ key.created }}
                  <span v-if="key.lastUsed"> • Last used {{ key.lastUsed }}</span>
                </div>
              </div>
              <UButton
                icon="i-lucide-trash"
                color="error"
                variant="ghost"
                size="sm"
                @click="deleteAPIKey(key.id)"
              />
            </div>
          </UCard>
        </div>
      </div>
    </UPageCard>

    <!-- Integrations -->
    <UPageCard title="Integrations" variant="subtle">
      <div class="space-y-4">
        <p class="text-sm text-muted">
          Connect LegalEase with your favorite tools and services
        </p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UCard
            v-for="integration in integrations"
            :key="integration.id"
            class="bg-muted/10"
          >
            <div class="flex items-start gap-4">
              <div class="p-3 bg-primary/10 rounded-lg">
                <UIcon :name="integration.icon" class="size-6 text-primary" />
              </div>
              <div class="flex-1 space-y-2">
                <div class="flex items-center justify-between">
                  <h4 class="font-semibold text-highlighted">
                    {{ integration.name }}
                  </h4>
                  <UToggle
                    :model-value="integration.enabled"
                    :disabled="!integration.configured"
                    @update:model-value="toggleIntegration(integration.id)"
                  />
                </div>
                <p class="text-sm text-muted">
                  {{ integration.description }}
                </p>
                <div class="flex items-center gap-2">
                  <UButton
                    :label="integration.configured ? 'Reconfigure' : 'Configure'"
                    icon="i-lucide-settings"
                    color="neutral"
                    variant="ghost"
                    size="xs"
                    @click="configureIntegration(integration.id)"
                  />
                  <UBadge
                    :label="integration.configured ? 'Configured' : 'Not Configured'"
                    :color="integration.configured ? 'success' : 'neutral'"
                    size="xs"
                    variant="subtle"
                  />
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </UPageCard>

    <!-- Webhooks -->
    <UPageCard title="Webhooks" variant="subtle">
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-muted">
            Receive real-time notifications when events occur
          </p>
          <UButton
            label="Add Webhook"
            icon="i-lucide-plus"
            color="primary"
            size="sm"
            @click="showNewWebhookModal = true"
          />
        </div>

        <div class="space-y-3">
          <UCard
            v-for="webhook in webhooks"
            :key="webhook.id"
            class="bg-muted/10"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 space-y-2">
                <div class="flex items-center gap-2">
                  <code class="text-sm">{{ webhook.url }}</code>
                  <UBadge
                    :label="webhook.enabled ? 'Active' : 'Disabled'"
                    :color="webhook.enabled ? 'success' : 'neutral'"
                    size="xs"
                  />
                </div>
                <div class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="event in webhook.events"
                    :key="event"
                    :label="event"
                    size="xs"
                    variant="subtle"
                  />
                </div>
                <p v-if="webhook.lastTriggered" class="text-xs text-muted">
                  Last triggered: {{ webhook.lastTriggered }}
                </p>
              </div>
              <div class="flex items-center gap-1">
                <UButton
                  icon="i-lucide-test-tube"
                  color="neutral"
                  variant="ghost"
                  size="sm"
                  title="Test Webhook"
                />
                <UButton
                  icon="i-lucide-trash"
                  color="error"
                  variant="ghost"
                  size="sm"
                  @click="deleteWebhook(webhook.id)"
                />
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </UPageCard>

    <!-- New API Key Modal -->
    <UModal v-model:open="showNewKeyModal" title="Create API Key">
      <template #body>
        <div class="space-y-4">
          <UFormField label="Key Name" required>
            <UInput
              v-model="newKeyName"
              placeholder="e.g., Production API Key"
            />
          </UFormField>

          <UFormField label="Permissions" required>
            <UCheckboxGroup
              v-model="newKeyPermissions"
              :items="permissionOptions"
            />
          </UFormField>

          <UAlert
            icon="i-lucide-alert-triangle"
            color="warning"
            variant="subtle"
            title="Keep your API key secure"
            description="Once created, you won't be able to see the full key again. Store it securely."
          />
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showNewKeyModal = false"
          />
          <UButton
            label="Create Key"
            icon="i-lucide-key"
            color="primary"
            :disabled="!newKeyName || newKeyPermissions.length === 0"
            @click="createAPIKey"
          />
        </div>
      </template>
    </UModal>

    <!-- New Webhook Modal -->
    <UModal v-model:open="showNewWebhookModal" title="Add Webhook">
      <template #body>
        <div class="space-y-4">
          <UFormField label="Webhook URL" required>
            <UInput
              v-model="newWebhookUrl"
              placeholder="https://example.com/webhooks"
              type="url"
            />
          </UFormField>

          <UFormField label="Events to Subscribe" required>
            <UCheckboxGroup
              v-model="newWebhookEvents"
              :items="eventOptions"
            />
          </UFormField>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton
            label="Cancel"
            color="neutral"
            variant="ghost"
            @click="showNewWebhookModal = false"
          />
          <UButton
            label="Create Webhook"
            icon="i-lucide-webhook"
            color="primary"
            :disabled="!newWebhookUrl || newWebhookEvents.length === 0"
            @click="createWebhook"
          />
        </div>
      </template>
    </UModal>
  </div>
</template>
