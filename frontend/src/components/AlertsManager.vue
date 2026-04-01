<script setup>
import AlertRuleList from "./AlertRuleList.vue";

const props = defineProps({
  alerts: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["remove", "view-history"]);
</script>

<template>
  <section class="ticker-manager">
    <div class="ticker-manager-head" style="display: flex; justify-content: space-between; align-items: baseline;">
      <p class="ticker-manager-title">ALARMS</p>
      <button class="text-btn" type="button" @click="emit('view-history')" style="font-size: 0.75rem; color: var(--accent); background: transparent; border: 0; cursor: pointer; font-weight: 600;">View History</button>
    </div>
    <AlertRuleList :alerts="alerts" @remove="emit('remove', $event)" />
  </section>
</template>
