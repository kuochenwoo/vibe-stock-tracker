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
  <section class="ticker-manager">
    <div class="panel-head">
      <div>
        <p class="label">Tracked Tickers</p>
      </div>
    </div>

    <div class="ticker-list">
      <article v-for="ticker in tickers" :key="ticker.code" class="ticker-row">
        <div class="ticker-copy">
          <p class="ticker-name">{{ ticker.name }}</p>
          <p class="ticker-meta">{{ ticker.code }} / {{ ticker.symbol }}</p>
        </div>
        <button class="ticker-remove" @click="props.onRemove(ticker.code)" aria-label="Remove ticker">
          ×
        </button>
      </article>
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
  </section>
</template>
