<script setup>
import { onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});

const flashToneByCode = ref({});
const previousPricesByCode = ref({});
const flashTimers = new Map();

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

function macroTone(value) {
  if (typeof value !== "number") return "price-flat";
  if (value > 0) return "price-up";
  if (value < 0) return "price-down";
  return "price-flat";
}

watch(
  () => props.items,
  (items) => {
    const activeCodes = new Set(items.map((item) => item.code));

    for (const [code, timer] of flashTimers.entries()) {
      if (!activeCodes.has(code)) {
        window.clearTimeout(timer);
        flashTimers.delete(code);
      }
    }

    const nextPreviousPrices = { ...previousPricesByCode.value };

    for (const item of items) {
      const nextPrice = item.price;
      const previousPrice = previousPricesByCode.value[item.code];
      nextPreviousPrices[item.code] = nextPrice;

      if (
        typeof nextPrice !== "number" ||
        typeof previousPrice !== "number" ||
        nextPrice === previousPrice
      ) {
        continue;
      }

      const tone = macroTone(item.change);
      if (!tone || tone === "price-flat") {
        delete flashToneByCode.value[item.code];
        continue;
      }

      flashToneByCode.value = {
        ...flashToneByCode.value,
        [item.code]: `macro-row-flash-${tone === "price-up" ? "up" : "down"}`,
      };

      const existingTimer = flashTimers.get(item.code);
      if (existingTimer) {
        window.clearTimeout(existingTimer);
      }

      const timer = window.setTimeout(() => {
        const nextFlashTones = { ...flashToneByCode.value };
        delete nextFlashTones[item.code];
        flashToneByCode.value = nextFlashTones;
        flashTimers.delete(item.code);
      }, 5000);

      flashTimers.set(item.code, timer);
    }

    previousPricesByCode.value = nextPreviousPrices;
  },
  { deep: true, immediate: true },
);

onBeforeUnmount(() => {
  for (const timer of flashTimers.values()) {
    window.clearTimeout(timer);
  }
  flashTimers.clear();
});
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
      <article
        v-for="item in items"
        :key="item.code"
        :class="['macro-row', flashToneByCode[item.code]]"
      >
        <div class="macro-copy">
          <p class="macro-name">{{ item.name }}</p>
          <span :class="['macro-badge', macroTone(item.change)]">{{ item.symbol }}</span>
        </div>
        <div class="macro-values">
          <strong>{{ formatPrice(item.price) }}</strong>
          <span :class="typeof item.change_percent === 'number' && item.change_percent >= 0 ? 'metric-live' : 'metric-offline'">
            {{ formatPercent(item.change_percent) }}
          </span>
        </div>
      </article>
    </div>
  </section>
</template>
