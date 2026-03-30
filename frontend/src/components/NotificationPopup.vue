<script setup>
defineProps({
  notice: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["dismiss"]);
</script>

<template>
  <Teleport to="body">
    <transition name="notice-fade">
      <section v-if="notice" class="notice-shell" aria-live="assertive" aria-atomic="true">
        <article class="notice-card">
          <div class="notice-accent"></div>
          <div class="notice-body">
            <p class="notice-label">{{ notice.label ?? "Price Alert" }}</p>
            <h2 class="notice-title">{{ notice.title }}</h2>
            <p class="notice-copy">{{ notice.body }}</p>
            <div class="notice-meta">
              <span>{{ notice.metaPrimary ?? notice.price }}</span>
              <span>{{ notice.metaSecondary ?? notice.time }}</span>
            </div>
          </div>
          <button class="notice-dismiss" type="button" @click="emit('dismiss')" aria-label="Dismiss notification">
            ×
          </button>
        </article>
      </section>
    </transition>
  </Teleport>
</template>
