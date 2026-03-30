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
  collapsed: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["update:collapsed"]);
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

function toggleCollapsed() {
  emit("update:collapsed", !props.collapsed);
}
</script>

<template>
  <section class="news-panel social-panel">
    <div class="panel-head">
      <div>
        <p class="label">SNS</p>
        <h2>Truth Social</h2>
      </div>
      <button class="collapse-toggle" type="button" :aria-label="collapsed ? 'Expand Truth Social panel' : 'Collapse Truth Social panel'" @click="toggleCollapsed">
        {{ collapsed ? "▾" : "−" }}
      </button>
    </div>

    <div v-if="!collapsed && items.length" class="social-feed">
      <article
        v-for="item in items"
        :key="item.id"
        class="social-post"
      >
        <div class="social-post-meta">
          <span class="news-source news-source-truth">{{ item.source }}</span>
          <span class="news-time">{{ formatPublishedAt(item.publishedAt) }}</span>
        </div>
        <h3>
          <a
            v-if="item.url"
            class="social-post-link"
            :href="item.url"
            target="_blank"
            rel="noreferrer"
          >
            {{ item.title }}
          </a>
          <span v-else>{{ item.title }}</span>
        </h3>
        <p>{{ item.summary }}</p>
        <div v-if="item.tags?.length" class="news-tags">
          <span v-for="tag in item.tags" :key="`${item.id}-${tag}`">{{ tag }}</span>
        </div>
      </article>
    </div>

    <p v-else-if="!collapsed && loading" class="sparkline-empty">Loading Truth Social posts.</p>
    <p v-else-if="!collapsed && error" class="sparkline-empty">{{ error }}</p>
    <p v-else-if="!collapsed" class="sparkline-empty">Waiting for Truth Social items.</p>
  </section>
</template>
