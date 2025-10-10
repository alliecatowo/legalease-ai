<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const caseId = route.params.id as string

const isGenerating = ref(false)
const reportGenerated = ref(false)
const selectedSections = ref<string[]>([
  'overview',
  'timeline',
  'parties',
  'legalIssues',
  'precedents',
  'documents',
  'risks',
  'strategy'
])

const sectionOptions = [
  { value: 'overview', label: 'Case Overview', description: 'Comprehensive case summary', icon: 'i-lucide-file-text' },
  { value: 'timeline', label: 'Chronological Timeline', description: 'Key events and dates', icon: 'i-lucide-calendar' },
  { value: 'parties', label: 'Party Analysis', description: 'Detailed party information', icon: 'i-lucide-users' },
  { value: 'legalIssues', label: 'Legal Issues', description: 'Core legal questions', icon: 'i-lucide-scale' },
  { value: 'precedents', label: 'Precedent Research', description: 'Relevant case law', icon: 'i-lucide-book-open' },
  { value: 'documents', label: 'Document Analysis', description: 'Key document findings', icon: 'i-lucide-files' },
  { value: 'risks', label: 'Risk Assessment', description: 'Potential risks and exposure', icon: 'i-lucide-alert-triangle' },
  { value: 'strategy', label: 'Strategic Recommendations', description: 'Suggested approaches', icon: 'i-lucide-lightbulb' }
]

// Mock case data - TODO: Replace with API call
const caseData = ref({
  id: caseId,
  name: 'Acme Corp v. Global Tech Inc',
  caseNumber: '2024-CV-12345',
  status: 'active',
  description: 'Breach of contract dispute involving software licensing agreements'
})

const researchReport = ref<any>(null)

async function generateReport() {
  isGenerating.value = true

  try {
    // TODO: Connect to AI backend
    await new Promise(resolve => setTimeout(resolve, 3000))

    researchReport.value = {
      generatedAt: new Date().toISOString(),
      caseId: caseData.value.id,
      caseName: caseData.value.name,
      sections: {
        overview: {
          summary: 'This case involves a complex breach of contract dispute between Acme Corporation (Plaintiff) and Global Tech Inc (Defendant) concerning a software licensing agreement executed in January 2024. The central dispute revolves around allegations of material breach, including failure to deliver promised features, performance issues, and disputed payment terms.',
          keyFacts: [
            'Contract execution date: January 15, 2024',
            'Disputed contract value: $2.5M annually',
            'Alleged breach period: March-June 2024',
            'Primary claim: Material breach of contract',
            'Damages sought: $5M plus specific performance'
          ],
          jurisdiction: 'Superior Court of California, County of Santa Clara',
          stage: 'Discovery phase'
        },
        timeline: {
          events: [
            { date: '2024-01-15', event: 'Contract Execution', description: 'Software licensing agreement signed', importance: 'critical' },
            { date: '2024-02-01', event: 'Implementation Begins', description: 'Global Tech begins software deployment', importance: 'high' },
            { date: '2024-03-15', event: 'First Complaint', description: 'Acme reports performance issues', importance: 'high' },
            { date: '2024-04-20', event: 'Formal Notice of Breach', description: 'Acme sends breach notification', importance: 'critical' },
            { date: '2024-05-30', event: 'Failed Mediation', description: 'Mediation attempt unsuccessful', importance: 'high' },
            { date: '2024-06-15', event: 'Lawsuit Filed', description: 'Acme files complaint in Superior Court', importance: 'critical' },
            { date: '2024-07-01', event: 'Answer Filed', description: 'Global Tech files answer and counterclaims', importance: 'critical' }
          ]
        },
        parties: {
          plaintiff: {
            name: 'Acme Corporation',
            type: 'Corporation (Delaware)',
            role: 'Software licensee',
            representation: 'Smith & Partners LLP',
            keyWitnesses: ['John Smith (CEO)', 'Jane Doe (CTO)', 'Bob Wilson (CFO)']
          },
          defendant: {
            name: 'Global Tech Inc',
            type: 'Corporation (California)',
            role: 'Software licensor',
            representation: 'Davis Law Group',
            keyWitnesses: ['Mike Johnson (CEO)', 'Sarah Lee (VP Engineering)']
          }
        },
        legalIssues: [
          {
            issue: 'Material Breach of Contract',
            description: 'Whether Global Tech\'s alleged failures constitute material breach',
            plaintiffPosition: 'Performance deficiencies and missing features are material breaches',
            defendantPosition: 'Issues are minor defects covered by warranty, not material breaches',
            applicableLaw: 'California Commercial Code § 2601-2725',
            strength: 'medium'
          },
          {
            issue: 'Damages Calculation',
            description: 'Appropriate measure and calculation of damages',
            plaintiffPosition: 'Expectation damages of $5M plus consequential damages',
            defendantPosition: 'Damages limited by contract cap and excluding consequential damages',
            applicableLaw: 'California Civil Code § 3300-3310',
            strength: 'high'
          },
          {
            issue: 'Force Majeure Application',
            description: 'Whether COVID-19 supply chain issues excuse performance',
            plaintiffPosition: 'Force majeure not applicable - issues predated pandemic',
            defendantPosition: 'Legitimate force majeure defense for partial non-performance',
            applicableLaw: 'Contract Section 14.2',
            strength: 'low'
          }
        ],
        precedents: [
          {
            case: 'Oracle USA v. SAP AG',
            citation: '2010 WL 3749797 (N.D. Cal. 2010)',
            relevance: 'Damages calculation for software licensing breach',
            holding: 'Established framework for calculating expectation damages in software disputes',
            impact: 'Favorable - supports plaintiff\'s damages theory'
          },
          {
            case: 'Applied Digital Solutions v. Millenium Partners',
            citation: '49 Cal. App. 4th 189 (1996)',
            relevance: 'Material breach standard',
            holding: 'Defined when performance deficiencies rise to material breach',
            impact: 'Mixed - provides framework but fact-specific'
          }
        ],
        documents: {
          total: 47,
          keyDocuments: [
            { name: 'Master License Agreement', date: '2024-01-15', importance: 'critical', issues: 2 },
            { name: 'Statement of Work', date: '2024-01-15', importance: 'critical', issues: 1 },
            { name: 'Email Chain - Performance Issues', date: '2024-03-20', importance: 'high', issues: 3 },
            { name: 'Breach Notice Letter', date: '2024-04-20', importance: 'critical', issues: 0 }
          ],
          gaps: [
            'Missing signed amendments referenced in emails',
            'Incomplete technical specifications',
            'Need discovery: internal Global Tech communications'
          ]
        },
        risks: [
          {
            risk: 'Insufficient documentary evidence',
            level: 'high',
            description: 'Key performance metrics not well-documented in contract',
            mitigation: 'Obtain expert testimony and industry standards'
          },
          {
            risk: 'Damages limitation clause',
            level: 'medium',
            description: 'Contract caps damages at $1M, below claimed amount',
            mitigation: 'Argue gross negligence exception or unconscionability'
          },
          {
            risk: 'Defendant counterclaims',
            level: 'medium',
            description: 'Global Tech alleges non-payment and scope creep',
            mitigation: 'Strong documentation of payment compliance'
          }
        ],
        strategy: {
          strengths: [
            'Clear contractual obligations documented',
            'Strong timeline of breach notifications',
            'Good email evidence of performance issues',
            'Expert witnesses available for technical issues'
          ],
          weaknesses: [
            'Damages calculation may face challenges',
            'Some performance metrics subjective',
            'Continued use of software after alleged breach',
            'Contractual damages limitations'
          ],
          recommendations: [
            {
              priority: 'high',
              action: 'Retain expert witness for software performance analysis',
              rationale: 'Critical to establish objective breach standards',
              timeline: 'Within 30 days'
            },
            {
              priority: 'high',
              action: 'Pursue early discovery of internal communications',
              rationale: 'May reveal knowledge of defects',
              timeline: 'Immediate'
            },
            {
              priority: 'medium',
              action: 'Consider settlement negotiations',
              rationale: 'Damages cap creates litigation risk',
              timeline: 'After initial discovery'
            }
          ],
          keyDepositions: [
            'Global Tech CTO - technical capabilities and representations',
            'Sales representatives - pre-contract promises',
            'Implementation team - performance issues and timeline'
          ]
        }
      }
    }

    reportGenerated.value = true
  } catch (err) {
    console.error('Failed to generate report:', err)
  } finally {
    isGenerating.value = false
  }
}

async function exportReport(format: 'pdf' | 'docx' | 'md') {
  // TODO: Implement export
  console.log('Exporting as:', format)
}

const sectionIcons: Record<string, string> = {
  overview: 'i-lucide-file-text',
  timeline: 'i-lucide-calendar',
  parties: 'i-lucide-users',
  legalIssues: 'i-lucide-scale',
  precedents: 'i-lucide-book-open',
  documents: 'i-lucide-files',
  risks: 'i-lucide-alert-triangle',
  strategy: 'i-lucide-lightbulb'
}
</script>

<template>
  <UDashboardPanel>
    <template #header>
      <UDashboardNavbar :title="`Deep Research: ${caseData.name}`">
        <template #leading>
          <UButton
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="ghost"
            :to="`/cases/${caseId}`"
          />
        </template>
        <template #trailing>
          <UButtonGroup v-if="reportGenerated">
            <UDropdownMenu>
              <UButton icon="i-lucide-download" label="Export" color="primary" variant="outline" />
              <template #content>
                <div class="p-1">
                  <UButton label="Export as PDF" icon="i-lucide-file" block variant="ghost" @click="exportReport('pdf')" />
                  <UButton label="Export as Word" icon="i-lucide-file-text" block variant="ghost" @click="exportReport('docx')" />
                  <UButton label="Export as Markdown" icon="i-lucide-file-code" block variant="ghost" @click="exportReport('md')" />
                </div>
              </template>
            </UDropdownMenu>
            <UButton
              icon="i-lucide-refresh-cw"
              color="neutral"
              variant="ghost"
              @click="generateReport"
            />
          </UButtonGroup>
        </template>
      </UDashboardNavbar>
    </template>

    <div class="p-6">
      <!-- Generation UI -->
      <div v-if="!reportGenerated" class="max-w-4xl mx-auto">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center size-16 bg-primary/10 rounded-full mb-4">
            <UIcon name="i-lucide-brain" class="size-8 text-primary" />
          </div>
          <h1 class="text-3xl font-bold mb-3">Deep Research Analysis</h1>
          <p class="text-muted max-w-2xl mx-auto">
            Generate a comprehensive AI-powered research report analyzing all aspects of this case,
            including legal issues, precedents, risks, and strategic recommendations.
          </p>
        </div>

        <!-- Section Selection -->
        <UCard :ui="{ body: 'space-y-6' }" class="mb-6">
          <div>
            <h3 class="font-semibold mb-4">Select Report Sections</h3>
            <UCheckboxGroup v-model="selectedSections" class="grid grid-cols-2 gap-3">
              <UCard v-for="option in sectionOptions" :key="option.value" :ui="{ body: 'p-3' }">
                <div class="flex items-start gap-3">
                  <UCheckbox :value="option.value" class="mt-1" />
                  <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                      <UIcon :name="option.icon" class="size-4 text-primary" />
                      <p class="font-medium text-sm">{{ option.label }}</p>
                    </div>
                    <p class="text-xs text-muted">{{ option.description }}</p>
                  </div>
                </div>
              </UCard>
            </UCheckboxGroup>
          </div>

          <UAlert
            icon="i-lucide-info"
            color="info"
            variant="soft"
            title="AI-Powered Analysis"
            description="This report uses AI to analyze all case documents, precedents, and data. Generation typically takes 2-3 minutes."
          />

          <UButton
            label="Generate Research Report"
            icon="i-lucide-sparkles"
            size="lg"
            block
            :loading="isGenerating"
            :disabled="selectedSections.length === 0 || isGenerating"
            @click="generateReport"
          >
            <template #leading>
              <UIcon name="i-lucide-sparkles" :class="{ 'animate-pulse': !isGenerating }" />
            </template>
          </UButton>
        </UCard>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4">
          <UCard :ui="{ body: 'p-4 text-center' }">
            <p class="text-3xl font-bold text-primary">47</p>
            <p class="text-sm text-muted mt-1">Documents</p>
          </UCard>
          <UCard :ui="{ body: 'p-4 text-center' }">
            <p class="text-3xl font-bold text-primary">156</p>
            <p class="text-sm text-muted mt-1">Data Points</p>
          </UCard>
          <UCard :ui="{ body: 'p-4 text-center' }">
            <p class="text-3xl font-bold text-primary">12</p>
            <p class="text-sm text-muted mt-1">Precedents</p>
          </UCard>
        </div>
      </div>

      <!-- Generated Report -->
      <div v-else-if="researchReport" class="max-w-5xl mx-auto space-y-6">
        <!-- Report Header -->
        <div class="text-center mb-8">
          <UBadge label="AI Generated" color="primary" variant="soft" class="mb-3" />
          <h1 class="text-3xl font-bold mb-2">{{ researchReport.caseName }}</h1>
          <p class="text-sm text-muted">
            Generated on {{ new Date(researchReport.generatedAt).toLocaleDateString() }}
          </p>
        </div>

        <!-- Overview Section -->
        <UCard v-if="selectedSections.includes('overview')" :ui="{ body: 'space-y-4' }">
          <div class="flex items-center gap-3 mb-4">
            <UIcon name="i-lucide-file-text" class="size-6 text-primary" />
            <h2 class="text-2xl font-bold">Case Overview</h2>
          </div>

          <p class="text-muted leading-relaxed">{{ researchReport.sections.overview.summary }}</p>

          <div>
            <h3 class="font-semibold mb-3">Key Facts</h3>
            <ul class="space-y-2">
              <li v-for="(fact, idx) in researchReport.sections.overview.keyFacts" :key="idx" class="flex items-start gap-2">
                <UIcon name="i-lucide-check-circle" class="size-4 text-success mt-0.5 shrink-0" />
                <span class="text-sm">{{ fact }}</span>
              </li>
            </ul>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="p-3 bg-muted/10 rounded-lg">
              <p class="text-xs text-muted mb-1">Jurisdiction</p>
              <p class="font-medium">{{ researchReport.sections.overview.jurisdiction }}</p>
            </div>
            <div class="p-3 bg-muted/10 rounded-lg">
              <p class="text-xs text-muted mb-1">Current Stage</p>
              <p class="font-medium">{{ researchReport.sections.overview.stage }}</p>
            </div>
          </div>
        </UCard>

        <!-- Timeline Section -->
        <UCard v-if="selectedSections.includes('timeline')" :ui="{ body: 'space-y-4' }">
          <div class="flex items-center gap-3 mb-4">
            <UIcon name="i-lucide-calendar" class="size-6 text-primary" />
            <h2 class="text-2xl font-bold">Chronological Timeline</h2>
          </div>

          <UTimeline
            :items="researchReport.sections.timeline.events.map((e: any) => ({
              ...e,
              date: new Date(e.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
              icon: e.importance === 'critical' ? 'i-lucide-alert-circle' : 'i-lucide-circle',
              color: e.importance === 'critical' ? 'error' : 'primary'
            }))"
          />
        </UCard>

        <!-- Legal Issues Section -->
        <UCard v-if="selectedSections.includes('legalIssues')" :ui="{ body: 'space-y-6' }">
          <div class="flex items-center gap-3 mb-4">
            <UIcon name="i-lucide-scale" class="size-6 text-primary" />
            <h2 class="text-2xl font-bold">Legal Issues</h2>
          </div>

          <div v-for="(issue, idx) in researchReport.sections.legalIssues" :key="idx" class="p-4 bg-muted/10 rounded-lg space-y-3">
            <div class="flex items-start justify-between gap-3">
              <h3 class="font-semibold">{{ issue.issue }}</h3>
              <UBadge
                :label="`${issue.strength} strength`"
                :color="issue.strength === 'high' ? 'success' : issue.strength === 'medium' ? 'warning' : 'neutral'"
                size="sm"
                variant="soft"
              />
            </div>
            <p class="text-sm text-muted">{{ issue.description }}</p>

            <div class="grid grid-cols-2 gap-4">
              <div class="p-3 bg-default rounded border border-default">
                <p class="text-xs font-medium text-primary mb-1">Plaintiff Position</p>
                <p class="text-sm">{{ issue.plaintiffPosition }}</p>
              </div>
              <div class="p-3 bg-default rounded border border-default">
                <p class="text-xs font-medium text-warning mb-1">Defendant Position</p>
                <p class="text-sm">{{ issue.defendantPosition }}</p>
              </div>
            </div>

            <p class="text-xs text-dimmed">
              <strong>Applicable Law:</strong> {{ issue.applicableLaw }}
            </p>
          </div>
        </UCard>

        <!-- Risks Section -->
        <UCard v-if="selectedSections.includes('risks')" :ui="{ body: 'space-y-4' }">
          <div class="flex items-center gap-3 mb-4">
            <UIcon name="i-lucide-alert-triangle" class="size-6 text-primary" />
            <h2 class="text-2xl font-bold">Risk Assessment</h2>
          </div>

          <div v-for="(risk, idx) in researchReport.sections.risks" :key="idx">
            <UAlert
              :color="risk.level === 'high' ? 'error' : risk.level === 'medium' ? 'warning' : 'neutral'"
              variant="soft"
            >
              <template #title>
                <div class="flex items-center justify-between">
                  <span>{{ risk.risk }}</span>
                  <UBadge :label="`${risk.level} risk`" size="sm" variant="outline" />
                </div>
              </template>
              <template #description>
                <div class="space-y-2 mt-2">
                  <p class="text-sm">{{ risk.description }}</p>
                  <p class="text-sm"><strong>Mitigation:</strong> {{ risk.mitigation }}</p>
                </div>
              </template>
            </UAlert>
          </div>
        </UCard>

        <!-- Strategy Section -->
        <UCard v-if="selectedSections.includes('strategy')" :ui="{ body: 'space-y-6' }">
          <div class="flex items-center gap-3 mb-4">
            <UIcon name="i-lucide-lightbulb" class="size-6 text-primary" />
            <h2 class="text-2xl font-bold">Strategic Recommendations</h2>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <h3 class="font-semibold mb-3 text-success">Strengths</h3>
              <ul class="space-y-2">
                <li v-for="(strength, idx) in researchReport.sections.strategy.strengths" :key="idx" class="flex items-start gap-2 text-sm">
                  <UIcon name="i-lucide-plus-circle" class="size-4 text-success mt-0.5 shrink-0" />
                  <span>{{ strength }}</span>
                </li>
              </ul>
            </div>

            <div>
              <h3 class="font-semibold mb-3 text-error">Weaknesses</h3>
              <ul class="space-y-2">
                <li v-for="(weakness, idx) in researchReport.sections.strategy.weaknesses" :key="idx" class="flex items-start gap-2 text-sm">
                  <UIcon name="i-lucide-minus-circle" class="size-4 text-error mt-0.5 shrink-0" />
                  <span>{{ weakness }}</span>
                </li>
              </ul>
            </div>
          </div>

          <div>
            <h3 class="font-semibold mb-4">Recommended Actions</h3>
            <div class="space-y-3">
              <UCard v-for="(rec, idx) in researchReport.sections.strategy.recommendations" :key="idx" :ui="{ body: 'p-4' }">
                <div class="flex items-start justify-between gap-3 mb-2">
                  <h4 class="font-medium">{{ rec.action }}</h4>
                  <UBadge
                    :label="rec.priority"
                    :color="rec.priority === 'high' ? 'error' : rec.priority === 'medium' ? 'warning' : 'neutral'"
                    size="sm"
                    variant="soft"
                  />
                </div>
                <p class="text-sm text-muted mb-2">{{ rec.rationale }}</p>
                <p class="text-xs text-dimmed"><strong>Timeline:</strong> {{ rec.timeline }}</p>
              </UCard>
            </div>
          </div>
        </UCard>
      </div>
    </div>
  </UDashboardPanel>
</template>
