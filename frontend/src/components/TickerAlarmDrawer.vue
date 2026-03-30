<script setup>
import { reactive, watch } from "vue";
import AlertRuleList from "./AlertRuleList.vue";

const props = defineProps({
  ticker: {
    type: Object,
    required: true,
  },
  alerts: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["close", "add-alert", "remove-alert"]);

const form = reactive({
  direction: "above",
  value: "",
});

watch(
  () => props.ticker?.code,
  () => {
    form.direction = "above";
    form.value = "";
  },
  { immediate: true },
);

function submit() {
  emit("add-alert", {
    market: props.ticker.code,
    direction: form.direction,
    value: form.value,
  });
  form.value = "";
}
</script>

<template>
  <aside class="alarm-drawer">
    <div class="panel-head">
      <div>
        <p class="label">{{ ticker.symbol }}</p>
        <h2>{{ ticker.name }}</h2>
      </div>
      <button class="icon-btn" type="button" @click="emit('close')">×</button>
    </div>

    <form class="alert-form" @submit.prevent="submit">
      <label>
        <span>Condition</span>
        <select v-model="form.direction">
          <option value="above">Above</option>
          <option value="below">Below</option>
        </select>
      </label>

      <label>
        <span>Alarm price</span>
        <input v-model="form.value" type="number" step="0.01" placeholder="Enter value" />
      </label>

      <button class="primary-btn" type="submit">Add alert</button>
    </form>

    <AlertRuleList :alerts="alerts" @remove="emit('remove-alert', $event)" />
  </aside>
</template>
