<script setup>
import AlertRuleList from "./AlertRuleList.vue";

const props = defineProps({
  alerts: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["remove"]);
</script>

<template>
  <section class="ticker-manager">
    <p class="ticker-manager-title">ALARMS</p>
    <AlertRuleList :alerts="alerts" @remove="emit('remove', $event)" />
  </section>
</template>
