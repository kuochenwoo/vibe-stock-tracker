<script setup>
import { computed } from "vue";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  eyebrow: {
    type: String,
    default: "Realtime News",
  },
  title: {
    type: String,
    default: "Wire",
  },
  collapsed: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:collapsed"]);

const featuredItem = computed(() => props.items[0] ?? null);
const secondaryItems = computed(() => props.items.slice(1));
const collapsed = computed(() => props.collapsed);

function formatPublishedAt(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function sourceTone(source) {
  if (source === "Bloomberg") return "news-source-bloomberg";
  if (source === "Truth Social") return "news-source-truth";
  return "";
}

function toggleCollapsed() {
  emit("update:collapsed", !props.collapsed);
}
</script>

<template>
  <section class="news-panel">
    <div class="panel-head">
      <div>
        <p class="label">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <button class="collapse-toggle" type="button" :aria-label="collapsed ? `Expand ${title} panel` : `Collapse ${title} panel`" @click="toggleCollapsed">
        {{ collapsed ? "▾" : "−" }}
      </button>
    </div>

    <div v-if="!collapsed && featuredItem" class="news-feed">
      <article class="news-feature">
        <div class="news-feature-meta">
          <span :class="['news-source', sourceTone(featuredItem.source)]">{{ featuredItem.source }}</span>
          <span class="news-time">{{ formatPublishedAt(featuredItem.publishedAt) }}</span>
        </div>
        <h3>{{ featuredItem.title }}</h3>
        <p>{{ featuredItem.summary }}</p>
        <div class="news-tags">
          <span v-for="tag in featuredItem.tags" :key="`${featuredItem.id}-${tag}`">{{ tag }}</span>
        </div>
      </article>

      <div class="news-list">
        <article
          v-for="item in secondaryItems"
          :key="item.id"
          class="news-item"
        >
          <div class="news-item-meta">
            <span :class="['news-source', sourceTone(item.source)]">{{ item.source }}</span>
            <span class="news-time">{{ formatPublishedAt(item.publishedAt) }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.summary }}</p>
        </article>
      </div>
    </div>

    <p v-else-if="!collapsed" class="sparkline-empty">Waiting for mock headlines.</p>
  </section>
</template>
