<script setup>
defineProps({
  alerts: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["remove"]);

function formatPrice(value) {
  if (typeof value !== "number") return "--";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
</script>

<template>
  <div v-if="alerts.length" class="alerts-list">
    <article
      v-for="rule in alerts"
      :key="rule.id"
      class="alert-item"
      :class="{ triggered: rule.triggered }"
    >
      <div>
        <p class="alert-title">{{ rule.marketTitle }}</p>
        <p class="alert-copy">
          Notify when price moves {{ rule.direction }} {{ formatPrice(rule.value) }}
        </p>
      </div>
      <button class="ghost-btn" @click="emit('remove', rule.id)">Delete</button>
    </article>
  </div>
  <p v-else class="empty-state">No alerts yet.</p>
</template>
