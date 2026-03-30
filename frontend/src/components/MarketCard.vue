<script setup>
defineProps({
  card: {
    type: Object,
    required: true,
  },
});

function formatPrice(value) {
  if (typeof value !== "number") return "--";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDelta(value) {
  if (typeof value !== "number") return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}

function formatPercent(value) {
  if (typeof value !== "number") return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}
</script>

<template>
  <article class="market-card">
    <div class="card-head">
      <div>
        <p class="label">{{ card.subtitle }}</p>
        <h2>{{ card.title }}</h2>
      </div>
      <span class="badge">{{ card.code }}</span>
    </div>

    <p class="price">{{ formatPrice(card.data?.price) }}</p>

    <div class="metrics">
      <div>
        <span>Change</span>
        <strong>{{ formatDelta(card.data?.change) }}</strong>
      </div>
      <div>
        <span>Change %</span>
        <strong>{{ formatPercent(card.data?.change_percent) }}</strong>
      </div>
      <div>
        <span>State</span>
        <strong>{{ card.data?.market_state ?? "--" }}</strong>
      </div>
      <div>
        <span>Symbol</span>
        <strong>{{ card.data?.symbol ?? "--" }}</strong>
      </div>
      <div>
        <span>Source</span>
        <strong>{{ card.data?.source ?? "--" }}</strong>
      </div>
    </div>

    <p v-if="card.data?.metadata?.fallback_symbol_used" class="provider-note">
      Requested {{ card.data.metadata.requested_symbol }}, using fallback
      {{ card.data.metadata.fallback_symbol_used }} for this provider.
    </p>
  </article>
</template>
