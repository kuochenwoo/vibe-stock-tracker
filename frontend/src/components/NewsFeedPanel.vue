<script setup>
import { computed } from "vue";

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
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
        <h3>
          <a
            v-if="featuredItem.url"
            class="news-item-link"
            :href="featuredItem.url"
            target="_blank"
            rel="noreferrer"
          >
            {{ featuredItem.title }}
          </a>
          <span v-else>{{ featuredItem.title }}</span>
        </h3>
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
          <h3>
            <a
              v-if="item.url"
              class="news-item-link"
              :href="item.url"
              target="_blank"
              rel="noreferrer"
          >
            {{ item.title }}
          </a>
          <span v-else>{{ item.title }}</span>
        </h3>
        </article>
      </div>
    </div>

    <p v-else-if="!collapsed && loading" class="sparkline-empty">Loading latest headlines.</p>
    <p v-else-if="!collapsed && error" class="sparkline-empty">{{ error }}</p>
    <p v-else-if="!collapsed" class="sparkline-empty">Waiting for wire headlines.</p>
  </section>
</template>
