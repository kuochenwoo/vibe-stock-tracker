<script setup>
defineProps({
  alertForm: {
    type: Object,
    required: true,
  },
  tickers: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["submit"]);
</script>

<template>
  <form class="alert-form" @submit.prevent="emit('submit')">
    <label>
      <span>Market</span>
      <select v-model="alertForm.market">
        <option v-for="ticker in tickers" :key="ticker.code" :value="ticker.code">
          {{ ticker.code }} / {{ ticker.name }}
        </option>
      </select>
    </label>

    <label>
      <span>Condition</span>
      <select v-model="alertForm.direction">
        <option value="above">Above</option>
        <option value="below">Below</option>
      </select>
    </label>

    <label>
      <span>Alarm price</span>
      <input v-model="alertForm.value" type="number" step="0.01" placeholder="Enter value" />
    </label>

    <button class="primary-btn" type="submit">Add alert</button>
  </form>
</template>
