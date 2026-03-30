<script setup>
defineProps({
  errors: {
    type: Array,
    required: true,
  },
});
</script>

<template>
  <section v-if="errors.length" class="errors-panel">
    <p class="label">Feed Errors</p>
    <ul>
      <li v-for="error in errors" :key="error">{{ error }}</li>
    </ul>
  </section>
</template>
