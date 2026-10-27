<template>
  <section class="course-page-hero" :class="{ 'has-actions': !!$slots.actions }">
    <div class="course-page-hero__content">
      <span v-if="eyebrow" class="course-page-hero__eyebrow">{{ eyebrow }}</span>
      <h1 class="course-page-hero__title">{{ title }}</h1>
      <p v-if="subtitle" class="course-page-hero__subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="course-page-hero__actions">
      <slot name="actions"></slot>
    </div>
  </section>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

<style scoped lang="less">
.course-page-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 0 14px;
}

.course-page-hero__content {
  max-width: 860px;
}

.course-page-hero__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 560;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.course-page-hero__eyebrow::before {
  content: '';
  width: 18px;
  height: 1px;
  background: currentColor;
}

.course-page-hero__title {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(30px, 3.4vw, 38px);
  line-height: 1.16;
  letter-spacing: 0.01em;
  font-weight: 560;
}

.course-page-hero__subtitle {
  margin: 12px 0 0;
  max-width: 680px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.72;
  letter-spacing: 0.01em;
}

.course-page-hero__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .course-page-hero {
    flex-direction: column;
    align-items: flex-start;
    padding-top: 18px;
  }
}
</style>
