<script setup lang="ts">
const { data: page } = await useAsyncData('index', () => queryCollection('index').first())

const title = page.value?.seo?.title || page.value?.title
const description = page.value?.seo?.description || page.value?.description

useSeoMeta({
  titleTemplate: '',
  title,
  ogTitle: title,
  description,
  ogDescription: description
})
</script>

<template>
  <div v-if="page">
    <UPageHero
      :title="page.title"
      :description="page.description"
      :links="page.hero.links"
    >
      <template #top>
        <HeroBackground />
      </template>

      <template #title>
        <MDC
          :value="page.title"
          unwrap="p"
        />
      </template>

      <PromotionalVideo />
    </UPageHero>

    <UPageSection
      v-for="(section, index) in page.sections"
      :key="index"
      :title="section.title"
      :description="section.description"
      :orientation="section.orientation"
      :reverse="section.reverse"
      :features="section.features"
    >
      <div class="relative">
        <UPageCard
          variant="subtle"
          class="rounded-2xl overflow-hidden"
        >
          <img
            :src="section.image"
            :alt="section.imageAlt"
            class="rounded-xl w-full shadow-lg"
          >
        </UPageCard>
      </div>
    </UPageSection>

    <UPageSection
      :title="page.features.title"
      :description="page.features.description"
    >
      <UPageGrid>
        <UPageCard
          v-for="(item, index) in page.features.items"
          :key="index"
          v-bind="item"
          spotlight
        />
      </UPageGrid>
    </UPageSection>

    <UPageSection
      title="Powerful Features in Action"
      description="See LegalEase AI's key capabilities with real interface screenshots showcasing transcription, discovery, case management, and document viewing."
    >
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/transcription_speaker_diarization.png" alt="AI Transcription" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold">AI Transcription</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">70x real-time transcription with speaker diarization</p>
          </div>
        </UPageCard>
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/discovery_items.png" alt="Discovery Management" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold">Discovery Items</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Comprehensive discovery document management</p>
          </div>
        </UPageCard>
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/cases_list.png" alt="Case Management" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold">Case Management</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Organize documents into structured cases</p>
          </div>
        </UPageCard>
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/document_metadata.png" alt="Document Viewer" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold">Document Viewer</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Native PDF viewer with search highlighting</p>
          </div>
        </UPageCard>
      </div>
    </UPageSection>

    <UPageSection
      title="Beautiful Interface with Theme Support"
      description="Experience LegalEase AI with multiple color themes and a clean, modern interface designed for legal professionals."
    >
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/search_hero_emerald_dark.png" alt="Emerald Dark Theme" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold text-emerald-600 dark:text-emerald-400">Emerald Dark</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Professional dark theme with emerald accents</p>
          </div>
        </UPageCard>
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/search_hero_pink_light.png" alt="Pink Light Theme" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold text-pink-600 dark:text-pink-400">Pink Light</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Clean light theme with pink accents</p>
          </div>
        </UPageCard>
        <UPageCard variant="subtle" class="rounded-2xl overflow-hidden">
          <img src="/search_hero_yellow_dark.png" alt="Yellow Dark Theme" class="rounded-xl w-full">
          <div class="p-4">
            <h3 class="font-semibold text-yellow-600 dark:text-yellow-400">Yellow Dark</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Modern dark theme with yellow accents</p>
          </div>
        </UPageCard>
      </div>
    </UPageSection>

    <USeparator />

    <UPageCTA
      v-bind="page.cta"
      variant="naked"
      class="overflow-hidden"
    >
      <LazyStarsBg />
    </UPageCTA>
  </div>
</template>
