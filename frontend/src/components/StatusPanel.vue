<script setup>
defineProps({
  connectionState: {
    type: String,
    required: true,
  },
  updatedAt: {
    type: String,
    default: null,
  },
  notificationPermission: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["enable-notifications"]);

function formatTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}
</script>

<template>
  <section class="status-panel">
    <div class="status-row">
      <span>Connection</span>
      <strong :class="`status-${connectionState}`">{{ connectionState }}</strong>
    </div>
    <div class="status-row">
      <span>Last Update</span>
      <strong>{{ formatTime(updatedAt) }}</strong>
    </div>
    <div class="status-row">
      <span>Notifications</span>
      <strong>{{ notificationPermission }}</strong>
    </div>
    <button class="primary-btn" @click="emit('enable-notifications')">
      Enable notifications
    </button>
  </section>
</template>
