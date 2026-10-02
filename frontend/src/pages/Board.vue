<template>
  <div>
    <h1 class="brand">本周看板</h1>
    <p class="muted">周卡片网格 · round-robin 落位后可去「对调」申请交换</p>
    <div style="display:flex;gap:8px;margin:12px 0">
      <button @click="generate">生成周表</button>
      <button class="ghost" @click="load">刷新</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <div class="week-grid">
      <article v-for="d in days" :key="d.day" class="week-card">
        <header>Day {{ d.day }}</header>
        <div v-for="c in d.cards" :key="c.id">
          <span class="chip">{{ c.task_title }}</span>
          <span class="chip coral">{{ c.member_name }}</span>
        </div>
        <p v-if="!d.cards.length" class="muted">空</p>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
// 只渲染投影接口的回包（days/cards 已按天分桶），不在本地重算归属
const days = ref([])
const err = ref('')
const weekId = 1
async function load() {
  err.value = ''
  try {
    const b = await api('/weeks/' + weekId + '/board')
    days.value = b.days || []
  } catch (e) { err.value = e.message }
}
async function generate() {
  err.value = ''
  try { await api('/weeks/' + weekId + '/generate', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = e.message }
}
onMounted(load)
</script>
