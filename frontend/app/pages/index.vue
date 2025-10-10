<template>
  <div class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-8">
      <header class="mb-8">
        <h1 class="text-4xl font-bold text-gray-900">
          LegalEase Dashboard
        </h1>
        <p class="mt-2 text-gray-600">
          AI-powered legal document analysis and compliance checking
        </p>
      </header>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Upload Documents Card -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-semibold mb-4">Upload Documents</h2>
          <p class="text-gray-600 mb-4">
            Upload legal documents for analysis
          </p>
          <button class="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">
            Upload
          </button>
        </div>

        <!-- Recent Documents Card -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-semibold mb-4">Recent Documents</h2>
          <p class="text-gray-600">
            View and manage your uploaded documents
          </p>
        </div>

        <!-- Analytics Card -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-semibold mb-4">Analytics</h2>
          <p class="text-gray-600">
            Track compliance and document insights
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Dashboard logic will be implemented here
</script>
