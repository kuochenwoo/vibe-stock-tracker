<script setup>
import { reactive, ref } from "vue";

const props = defineProps({
  tickers: {
    type: Array,
    required: true,
  },
  onAdd: {
    type: Function,
    required: true,
  },
  onRemove: {
    type: Function,
    required: true,
  },
});

const form = reactive({
  code: "",
  symbol: "",
  name: "",
});
const errorMessage = ref("");
const saving = ref(false);

async function submit() {
  errorMessage.value = "";
  saving.value = true;

  try {
    await props.onAdd({
      code: form.code,
      symbol: form.symbol,
      name: form.name,
    });
    form.code = "";
    form.symbol = "";
    form.name = "";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Failed to add ticker.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="alerts-panel">
    <div class="panel-head">
      <div>
        <p class="label">Tracked Tickers</p>
        <h2>Manage instruments</h2>
      </div>
    </div>

    <form class="alert-form" @submit.prevent="submit">
      <label>
        <span>Code</span>
        <input v-model="form.code" type="text" placeholder="GC=F" />
      </label>
      <label>
        <span>Provider symbol</span>
        <input v-model="form.symbol" type="text" placeholder="GC=F" />
      </label>
      <label>
        <span>Display name</span>
        <input v-model="form.name" type="text" placeholder="Gold Futures" />
      </label>
      <button class="primary-btn" type="submit" :disabled="saving">
        {{ saving ? "Saving..." : "Add ticker" }}
      </button>
    </form>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <div class="alerts-list">
      <article v-for="ticker in tickers" :key="ticker.code" class="alert-item">
        <div>
          <p class="alert-title">{{ ticker.name }}</p>
          <p class="alert-copy">{{ ticker.code }} / {{ ticker.symbol }}</p>
        </div>
        <button class="ghost-btn" @click="props.onRemove(ticker.code)">Delete</button>
      </article>
    </div>
  </section>
</template>
