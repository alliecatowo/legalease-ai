<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  actionType: 'summarize' | 'analyze' | 'extract' | 'research' | 'compare'
  targetId?: string
  targetType?: 'document' | 'case' | 'transcript' | 'clause'
  label?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'solid' | 'outline' | 'soft' | 'ghost'
  block?: boolean
}>()

const emit = defineEmits<{
  'complete': [result: any]
  'error': [error: string]
}>()

const isProcessing = ref(false)
const showResultModal = ref(false)
const result = ref<any>(null)
const error = ref<string | null>(null)

const actionConfig = {
  summarize: {
    label: 'AI Summary',
    icon: 'i-lucide-sparkles',
    description: 'Generate intelligent summary',
    processingText: 'Analyzing and summarizing...'
  },
  analyze: {
    label: 'AI Analysis',
    icon: 'i-lucide-brain',
    description: 'Deep analysis with insights',
    processingText: 'Performing deep analysis...'
  },
  extract: {
    label: 'Extract Key Info',
    icon: 'i-lucide-scan-search',
    description: 'Extract entities and clauses',
    processingText: 'Extracting information...'
  },
  research: {
    label: 'Deep Research',
    icon: 'i-lucide-search',
    description: 'Comprehensive research report',
    processingText: 'Conducting research...'
  },
  compare: {
    label: 'AI Compare',
    icon: 'i-lucide-git-compare',
    description: 'Compare and find differences',
    processingText: 'Comparing documents...'
  }
}

const config = actionConfig[props.actionType]

async function handleAction() {
  isProcessing.value = true
  error.value = null

  try {
    // TODO: Connect to actual AI backend endpoint
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock result based on action type
    result.value = getMockResult(props.actionType)
    showResultModal.value = true
    emit('complete', result.value)
  } catch (err) {
    error.value = 'Failed to process request'
    emit('error', error.value)
  } finally {
    isProcessing.value = false
  }
}

function getMockResult(type: string) {
  switch (type) {
    case 'summarize':
      return {
        summary: 'This document outlines the key terms of the software licensing agreement between Acme Corp and Global Tech Inc. The agreement establishes a 3-year license term with annual renewal options, defines usage rights for up to 500 users, and includes provisions for support, maintenance, and liability limitations.',
        keyPoints: [
          'License duration: 3 years with renewal options',
          'Maximum users: 500 concurrent',
          'Support: 24/7 technical support included',
          'Liability cap: $1M per incident',
          'Payment terms: Annual upfront'
        ],
        confidence: 0.94
      }
    case 'analyze':
      return {
        analysis: 'The contract shows several areas of potential concern. The liability limitation clause (Section 8) caps damages at $1M, which may be insufficient given the critical nature of the software. The termination clause (Section 12) allows for unilateral termination with 30 days notice, exposing the client to business continuity risks.',
        risks: [
          { level: 'high', description: 'Insufficient liability cap for critical systems', section: '8.2' },
          { level: 'medium', description: 'Short termination notice period', section: '12.1' },
          { level: 'low', description: 'Vague performance metrics', section: '5.3' }
        ],
        opportunities: [
          'Strong IP protection provisions',
          'Favorable audit rights',
          'Flexible scaling terms'
        ]
      }
    case 'extract':
      return {
        entities: [
          { type: 'organization', value: 'Acme Corporation', count: 15 },
          { type: 'organization', value: 'Global Tech Inc', count: 12 },
          { type: 'person', value: 'John Smith', count: 3, role: 'CEO' },
          { type: 'date', value: '2024-01-15', context: 'Effective Date' },
          { type: 'amount', value: '$2.5M', context: 'Annual License Fee' }
        ],
        clauses: [
          { type: 'payment', section: '4', importance: 'high' },
          { type: 'termination', section: '12', importance: 'high' },
          { type: 'liability', section: '8', importance: 'critical' },
          { type: 'confidentiality', section: '9', importance: 'high' }
        ]
      }
    case 'research':
      return {
        overview: 'Comprehensive analysis of Acme Corp v. Global Tech Inc case',
        sections: [
          {
            title: 'Case Background',
            content: 'The case involves a breach of contract dispute arising from a software licensing agreement...'
          },
          {
            title: 'Legal Issues',
            content: 'Three primary legal issues: (1) Material breach, (2) Damages calculation, (3) Force majeure applicability...'
          },
          {
            title: 'Precedent Analysis',
            content: 'Similar cases show mixed outcomes. Key precedent: Oracle v. SAP (2010) established standards for...'
          }
        ],
        relatedCases: 5,
        documentsAnalyzed: 47
      }
    default:
      return { message: 'Action completed successfully' }
  }
}
</script>

<template>
  <div>
    <UButton
      :label="label || config.label"
      :icon="isProcessing ? 'i-lucide-loader' : config.icon"
      :size="size || 'md'"
      :variant="variant || 'solid'"
      :block="block"
      color="primary"
      :loading="isProcessing"
      :disabled="isProcessing"
      @click="handleAction"
    >
      <template v-if="!label" #leading>
        <UIcon
          :name="isProcessing ? 'i-lucide-loader' : 'i-lucide-sparkles'"
          :class="{ 'animate-spin': isProcessing, 'animate-pulse': !isProcessing }"
        />
      </template>
    </UButton>

    <!-- Result Modal -->
    <UModal v-model:open="showResultModal" :ui="{ content: 'max-w-3xl' }">
      <template #header>
        <div class="flex items-center gap-3">
          <UIcon :name="config.icon" class="size-6 text-primary" />
          <div>
            <h3 class="text-xl font-semibold">{{ config.label }}</h3>
            <p class="text-sm text-muted">Generated by AI</p>
          </div>
        </div>
      </template>

      <template #body>
        <div class="space-y-6">
          <!-- Summarize Result -->
          <div v-if="actionType === 'summarize' && result">
            <div class="mb-4">
              <h4 class="font-semibold mb-2">Summary</h4>
              <p class="text-muted leading-relaxed">{{ result.summary }}</p>
            </div>

            <div v-if="result.keyPoints">
              <h4 class="font-semibold mb-3">Key Points</h4>
              <ul class="space-y-2">
                <li v-for="(point, idx) in result.keyPoints" :key="idx" class="flex items-start gap-2">
                  <UIcon name="i-lucide-check-circle" class="size-4 text-success mt-0.5 shrink-0" />
                  <span class="text-sm">{{ point }}</span>
                </li>
              </ul>
            </div>

            <UAlert
              v-if="result.confidence"
              icon="i-lucide-info"
              color="info"
              variant="soft"
              class="mt-4"
              :title="`Confidence: ${Math.round(result.confidence * 100)}%`"
              description="AI-generated summary. Please review for accuracy."
            />
          </div>

          <!-- Analysis Result -->
          <div v-else-if="actionType === 'analyze' && result">
            <div class="mb-4">
              <h4 class="font-semibold mb-2">Analysis</h4>
              <p class="text-muted leading-relaxed">{{ result.analysis }}</p>
            </div>

            <div v-if="result.risks" class="mb-4">
              <h4 class="font-semibold mb-3">Identified Risks</h4>
              <div class="space-y-2">
                <UAlert
                  v-for="(risk, idx) in result.risks"
                  :key="idx"
                  :color="risk.level === 'high' ? 'error' : risk.level === 'medium' ? 'warning' : 'neutral'"
                  variant="soft"
                >
                  <template #title>
                    <div class="flex items-center justify-between">
                      <span>{{ risk.description }}</span>
                      <UBadge :label="`Section ${risk.section}`" size="sm" variant="outline" />
                    </div>
                  </template>
                </UAlert>
              </div>
            </div>

            <div v-if="result.opportunities">
              <h4 class="font-semibold mb-3">Opportunities</h4>
              <ul class="space-y-2">
                <li v-for="(opp, idx) in result.opportunities" :key="idx" class="flex items-start gap-2">
                  <UIcon name="i-lucide-thumbs-up" class="size-4 text-success mt-0.5 shrink-0" />
                  <span class="text-sm">{{ opp }}</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Extract Result -->
          <div v-else-if="actionType === 'extract' && result">
            <div v-if="result.entities" class="mb-4">
              <h4 class="font-semibold mb-3">Extracted Entities</h4>
              <div class="grid grid-cols-2 gap-3">
                <UCard v-for="(entity, idx) in result.entities" :key="idx" :ui="{ body: 'p-3' }">
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <p class="font-medium truncate">{{ entity.value }}</p>
                      <p class="text-xs text-muted capitalize">{{ entity.type }}</p>
                      <p v-if="entity.context" class="text-xs text-dimmed mt-1">{{ entity.context }}</p>
                    </div>
                    <UBadge v-if="entity.count" :label="String(entity.count)" size="sm" variant="soft" />
                  </div>
                </UCard>
              </div>
            </div>

            <div v-if="result.clauses">
              <h4 class="font-semibold mb-3">Key Clauses</h4>
              <div class="space-y-2">
                <div v-for="(clause, idx) in result.clauses" :key="idx" class="flex items-center justify-between p-3 bg-muted/10 rounded-lg">
                  <div class="flex items-center gap-3">
                    <UIcon name="i-lucide-file-text" class="size-4 text-primary" />
                    <div>
                      <p class="font-medium capitalize">{{ clause.type }}</p>
                      <p class="text-xs text-muted">Section {{ clause.section }}</p>
                    </div>
                  </div>
                  <UBadge
                    :label="clause.importance"
                    :color="clause.importance === 'critical' ? 'error' : clause.importance === 'high' ? 'warning' : 'neutral'"
                    size="sm"
                    variant="soft"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Research Result -->
          <div v-else-if="actionType === 'research' && result">
            <div class="mb-4">
              <p class="text-muted">{{ result.overview }}</p>
            </div>

            <div v-if="result.sections" class="space-y-4">
              <UAccordion
                :items="result.sections.map((s, idx) => ({ label: s.title, slot: `section-${idx}` }))"
                :default-value="['0']"
              >
                <template v-for="(section, idx) in result.sections" :key="idx" #[`section-${idx}`]>
                  <p class="text-sm text-muted">{{ section.content }}</p>
                </template>
              </UAccordion>
            </div>

            <div class="grid grid-cols-2 gap-3 mt-4">
              <UCard :ui="{ body: 'p-3 text-center' }">
                <p class="text-2xl font-bold text-primary">{{ result.relatedCases }}</p>
                <p class="text-xs text-muted mt-1">Related Cases</p>
              </UCard>
              <UCard :ui="{ body: 'p-3 text-center' }">
                <p class="text-2xl font-bold text-primary">{{ result.documentsAnalyzed }}</p>
                <p class="text-xs text-muted mt-1">Documents Analyzed</p>
              </UCard>
            </div>
          </div>

          <!-- Generic Result -->
          <div v-else class="text-center py-8">
            <UIcon name="i-lucide-check-circle" class="size-16 text-success mx-auto mb-4" />
            <p class="text-muted">{{ result?.message || 'Action completed successfully' }}</p>
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-between">
          <UButton
            label="Copy Result"
            icon="i-lucide-copy"
            color="neutral"
            variant="outline"
            @click="() => {}"
          />
          <div class="flex items-center gap-2">
            <UButton
              label="Export"
              icon="i-lucide-download"
              color="neutral"
              variant="ghost"
              @click="() => {}"
            />
            <UButton
              label="Close"
              color="primary"
              @click="showResultModal = false"
            />
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
