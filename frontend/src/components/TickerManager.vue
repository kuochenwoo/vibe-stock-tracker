<script setup>
import { nextTick, reactive, ref, watch } from "vue";

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
const isComposerOpen = ref(false);
const saving = ref(false);
const triggerButton = ref(null);
const codeInput = ref(null);

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
    isComposerOpen.value = false;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Failed to add ticker.";
  } finally {
    saving.value = false;
  }
}

function openComposer() {
  isComposerOpen.value = true;
}

function closeComposer() {
  isComposerOpen.value = false;
  nextTick(() => {
    triggerButton.value?.focus();
  });
}

watch(isComposerOpen, async (open) => {
  if (!open) return;
  errorMessage.value = "";
  await nextTick();
  codeInput.value?.focus();
});
</script>

<template>
  <section class="ticker-manager">
    <div class="panel-head ticker-head">
      <div>
        <p class="label">Tracked Tickers</p>
      </div>
      <button ref="triggerButton" class="icon-btn" @click="openComposer">+</button>
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

    <Teleport to="body">
      <div v-if="isComposerOpen" class="ticker-modal-backdrop" @click.self="closeComposer">
        <div
          class="ticker-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ticker-modal-title"
          @keydown.esc="closeComposer"
        >
          <div class="panel-head">
            <div>
              <p class="label">Add Ticker</p>
              <h2 id="ticker-modal-title">New instrument</h2>
            </div>
            <button class="icon-btn" @click="closeComposer">x</button>
          </div>

          <form class="alert-form" @submit.prevent="submit">
            <label>
              <span>Code</span>
              <input ref="codeInput" v-model="form.code" type="text" placeholder="GC=F" />
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
        </div>
      </div>
    </Teleport>
  </section>
</template>
