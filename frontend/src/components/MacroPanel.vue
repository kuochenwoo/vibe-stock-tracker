<script setup>
const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});

function formatPrice(value) {
  if (typeof value !== "number") return "--";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPercent(value) {
  if (typeof value !== "number") return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}
</script>

<template>
  <section class="news-panel">
    <div class="panel-head">
      <div>
        <p class="label">Market Macro</p>
        <h2>US Futures</h2>
      </div>
    </div>

    <div class="macro-list">
      <article v-for="item in items" :key="item.code" class="macro-row">
        <div class="macro-copy">
          <p class="macro-name">{{ item.name }}</p>
          <p class="macro-symbol">{{ item.symbol }}</p>
        </div>
        <div class="macro-values">
          <strong>{{ formatPrice(item.price) }}</strong>
          <span :class="item.change_percent >= 0 ? 'metric-live' : 'metric-offline'">
            {{ formatPercent(item.change_percent) }}
          </span>
        </div>
      </article>
    </div>
  </section>
</template>
