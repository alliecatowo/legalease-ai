<script setup lang="ts">
const props = defineProps<{
  score: number
  size?: 'xs' | 'sm' | 'md' | 'lg'
  showLabel?: boolean
  showTooltip?: boolean
}>()

// Determine color and icon based on score
const importance = computed(() => {
  if (props.score >= 0.8) {
    return {
      level: 'Critical',
      color: 'red',
      icon: 'i-lucide-alert-triangle',
      gradient: 'from-red-500 to-red-600',
      stars: 5
    }
  } else if (props.score >= 0.6) {
    return {
      level: 'High',
      color: 'amber',
      icon: 'i-lucide-star',
      gradient: 'from-amber-500 to-amber-600',
      stars: 4
    }
  } else if (props.score >= 0.4) {
    return {
      level: 'Medium',
      color: 'blue',
      icon: 'i-lucide-info',
      gradient: 'from-blue-500 to-blue-600',
      stars: 3
    }
  } else if (props.score >= 0.2) {
    return {
      level: 'Low',
      color: 'green',
      icon: 'i-lucide-check',
      gradient: 'from-green-500 to-green-600',
      stars: 2
    }
  } else {
    return {
      level: 'Minimal',
      color: 'neutral',
      icon: 'i-lucide-minus',
      gradient: 'from-gray-500 to-gray-600',
      stars: 1
    }
  }
})

const sizeClasses = computed(() => {
  const sizes = {
    xs: {
      badge: 'text-xs px-1.5 py-0.5',
      icon: 'size-3',
      star: 'size-2.5'
    },
    sm: {
      badge: 'text-sm px-2 py-1',
      icon: 'size-3.5',
      star: 'size-3'
    },
    md: {
      badge: 'text-base px-3 py-1.5',
      icon: 'size-4',
      star: 'size-3.5'
    },
    lg: {
      badge: 'text-lg px-4 py-2',
      icon: 'size-5',
      star: 'size-4'
    }
  }
  return sizes[props.size || 'md']
})

const tooltipText = computed(() => {
  return `Importance: ${importance.value.level} (${(props.score * 100).toFixed(0)}%)`
})
</script>

<template>
  <UTooltip
    v-if="showTooltip !== false"
    :text="tooltipText"
  >
    <div
      :class="[
        'inline-flex items-center gap-1 rounded-full font-semibold',
        'bg-gradient-to-r',
        importance.gradient,
        'text-white shadow-sm',
        sizeClasses.badge
      ]"
    >
      <UIcon :name="importance.icon" :class="sizeClasses.icon" />

      <!-- Star rating -->
      <div class="flex items-center gap-0.5">
        <UIcon
          v-for="star in importance.stars"
          :key="star"
          name="i-lucide-star"
          :class="[sizeClasses.star, 'fill-current']"
        />
      </div>

      <!-- Label -->
      <span v-if="showLabel" class="ml-1">
        {{ importance.level }}
      </span>

      <!-- Score percentage -->
      <span v-if="showLabel" class="ml-1 opacity-75">
        {{ (score * 100).toFixed(0) }}%
      </span>
    </div>
  </UTooltip>

  <div
    v-else
    :class="[
      'inline-flex items-center gap-1 rounded-full font-semibold',
      'bg-gradient-to-r',
      importance.gradient,
      'text-white shadow-sm',
      sizeClasses.badge
    ]"
  >
    <UIcon :name="importance.icon" :class="sizeClasses.icon" />

    <!-- Star rating -->
    <div class="flex items-center gap-0.5">
      <UIcon
        v-for="star in importance.stars"
        :key="star"
        name="i-lucide-star"
        :class="[sizeClasses.star, 'fill-current']"
      />
    </div>

    <!-- Label -->
    <span v-if="showLabel" class="ml-1">
      {{ importance.level }}
    </span>

    <!-- Score percentage -->
    <span v-if="showLabel" class="ml-1 opacity-75">
      {{ (score * 100).toFixed(0) }}%
    </span>
  </div>
</template>
