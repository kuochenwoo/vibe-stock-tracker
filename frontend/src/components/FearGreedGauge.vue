<script setup>
import { computed } from "vue";

const props = defineProps({
  snapshot: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
  collapsed: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:collapsed"]);

const segments = [
  { label: "Extreme Fear", start: 0, end: 25, color: "#d14343" },
  { label: "Fear", start: 25, end: 45, color: "#ef6c00" },
  { label: "Neutral", start: 45, end: 55, color: "#ffb300" },
  { label: "Greed", start: 55, end: 75, color: "#43a047" },
  { label: "Extreme Greed", start: 75, end: 100, color: "#1565c0" },
];

const score = computed(() => props.snapshot?.value ?? null);
const rating = computed(() => props.snapshot?.rating ?? "--");
const currentSegment = computed(() => {
  if (typeof score.value !== "number") return null;
  return (
    segments.find((segment) => score.value >= segment.start && score.value <= segment.end) ?? null
  );
});
const compactColor = computed(() => currentSegment.value?.color ?? "var(--muted)");
const collapsed = computed(() => props.collapsed);

const needleTransform = computed(() => {
  const value = typeof score.value === "number" ? score.value : 50;
  const angle = -90 + (value / 100) * 180;
  return `rotate(${angle} 100 100)`;
});

const readingRows = computed(() => [
  { label: "Previous close", reading: props.snapshot?.previous_close },
  { label: "1 week ago", reading: props.snapshot?.one_week_ago },
  { label: "1 month ago", reading: props.snapshot?.one_month_ago },
  { label: "1 year ago", reading: props.snapshot?.one_year_ago },
]);

function polarToCartesian(cx, cy, radius, angleDeg) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angleRad),
    y: cy + radius * Math.sin(angleRad),
  };
}

function describeArc(startValue, endValue) {
  const startAngle = -90 + (startValue / 100) * 180;
  const endAngle = -90 + (endValue / 100) * 180;
  const start = polarToCartesian(100, 100, 78, startAngle);
  const end = polarToCartesian(100, 100, 78, endAngle);
  const largeArcFlag = endValue - startValue > 50 ? 1 : 0;
  return `M ${start.x} ${start.y} A 78 78 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
}

function markerX(value) {
  return 24 + (value / 100) * 152;
}

function formatReading(reading) {
  if (!reading || typeof reading.value !== "number") return "--";
  return `${reading.value}`;
}

function readingColor(reading) {
  if (!reading || typeof reading.value !== "number") return "var(--muted)";
  return (
    segments.find((segment) => reading.value >= segment.start && reading.value <= segment.end)
      ?.color ?? "var(--muted)"
  );
}

function formatUpdatedAt(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function toggleCollapsed() {
  emit("update:collapsed", !props.collapsed);
}
</script>

<template>
  <section class="fear-greed-card">
    <div class="panel-head">
      <div>
        <p class="label">Market Sentiment</p>
        <div class="fear-greed-title-row">
          <h2>
            <span class="fear-greed-source-wrap">
              <a
                class="fear-greed-title-link"
                :href="snapshot?.source_url ?? 'https://edition.cnn.com/markets/fear-and-greed'"
                target="_blank"
                rel="noreferrer"
              >
                Fear &amp; Greed
              </a>
              <span class="fear-greed-source-tooltip">Source: CNN</span>
            </span>
          </h2>
          <strong
            v-if="collapsed"
            class="fear-greed-inline-value"
            :style="{ color: compactColor }"
          >
            {{ score ?? "--" }}
          </strong>
        </div>
      </div>
      <button class="collapse-toggle" type="button" :aria-label="collapsed ? 'Expand fear and greed panel' : 'Collapse fear and greed panel'" @click="toggleCollapsed">
        {{ collapsed ? "▾" : "−" }}
      </button>
    </div>

    <div v-if="error" class="fear-greed-state">{{ error }}</div>
    <div v-else-if="loading && !snapshot" class="fear-greed-state">Loading fear &amp; greed index...</div>
    <div v-else-if="collapsed" class="fear-greed-collapsed"></div>
    <div v-else class="fear-greed-body">
      <div class="gauge-score-head">
        <strong>{{ score ?? "--" }}</strong>
        <span :style="{ color: currentSegment?.color ?? 'var(--muted)' }">{{ rating }}</span>
      </div>

      <div class="gauge-wrap">
        <svg class="gauge-chart" viewBox="0 0 200 118" aria-hidden="true">
          <path
            v-for="segment in segments"
            :key="segment.label"
            :d="describeArc(segment.start, segment.end)"
            class="gauge-segment"
            :style="{ stroke: segment.color }"
          />
          <line
            v-for="segment in [0, 25, 45, 55, 75, 100]"
            :key="segment"
            class="gauge-divider"
            :x1="markerX(segment)"
            :x2="markerX(segment)"
            y1="92"
            y2="104"
          />
          <g class="gauge-needle" :transform="needleTransform">
            <line x1="100" y1="92" x2="100" y2="28" />
            <circle cx="100" cy="92" r="5" />
          </g>
        </svg>
      </div>

      <div class="gauge-scale">
        <span>0</span>
        <span>25</span>
        <span>45</span>
        <span>55</span>
        <span>75</span>
        <span>100</span>
      </div>

      <p class="fear-greed-updated">Updated {{ formatUpdatedAt(snapshot?.updated_at) }}</p>

      <div class="fear-greed-readings">
        <div v-for="row in readingRows" :key="row.label" class="fear-greed-reading">
          <span>{{ row.label }}</span>
          <strong :style="{ color: readingColor(row.reading) }">{{ formatReading(row.reading) }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>
