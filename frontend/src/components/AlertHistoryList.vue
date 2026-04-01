<script setup>
defineProps({
  history: {
    type: Array,
    required: true,
  },
  trackedTickers: {
    type: Array,
    required: true,
  }
});

function formatPrice(value) {
  if (typeof value !== "number") return "--";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function getMarketName(code, trackedTickers) {
    return trackedTickers.find(t => t.code === code)?.name || code;
}
</script>

<template>
  <div v-if="history.length" class="alerts-list alert-history-list">
    <article
      v-for="item in history"
      :key="item.id"
      class="alert-item"
    >
      <div class="alert-content">
        <div class="alert-header">
            <p class="alert-title">{{ getMarketName(item.market, trackedTickers) }}</p>
            <span class="alert-time">{{ formatTime(item.triggered_at) }}</span>
        </div>
        <p class="alert-copy">
          Price moved {{ item.direction }} {{ formatPrice(item.threshold) }} (Hit: {{ formatPrice(item.price) }})
        </p>
      </div>
    </article>
  </div>
  <p v-else class="empty-state">No trigger history yet.</p>
</template>

<style scoped>
.alert-history-list {
    max-height: 400px;
    overflow-y: auto;
    padding-right: 8px;
}
.alert-content {
    width: 100%;
}
.alert-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}
.alert-time {
    font-size: 0.75rem;
    color: var(--muted);
}
/* Scrollbar styling */
.alert-history-list::-webkit-scrollbar {
  width: 6px;
}
.alert-history-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(91, 107, 134, 0.2);
}
</style>
