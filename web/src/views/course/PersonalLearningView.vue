<template>
  <div class="course-page">
    <CourseTopbar @logout="userStore.logout()" @switch-account="userStore.logout()" />
    <main class="page-shell personal-learning">
      <CoursePageHero
        eyebrow="Personal learning"
        title="我的学情"
        subtitle="根据近 30 天的习题作答，找到需要复习的知识点，再用专项自测检验复习效果。"
      />

      <p v-if="loading" role="status">正在加载学情…</p>
      <div v-else-if="error" role="alert">
        <p>学情加载失败，请重试。</p>
        <a-button @click="loadAnalysis">重新加载</a-button>
      </div>
      <section v-else-if="!attemptCount" class="learning-panel">
        <h2>先完成一次习题自测</h2>
        <p>提交答案后，这里会按知识点汇总你的作答和错题。</p>
        <RouterLink to="/exercises">前往习题推荐</RouterLink>
      </section>

      <template v-else>
        <dl class="learning-overview">
          <div class="learning-panel">
            <dt>作答次数</dt>
            <dd>{{ attemptCount }}</dd>
          </div>
          <div class="learning-panel">
            <dt>答错次数</dt>
            <dd>{{ wrongCount }}</dd>
          </div>
          <div class="learning-panel">
            <dt>作答正确率</dt>
            <dd>{{ accuracy(attemptCount, wrongCount) }}</dd>
          </div>
        </dl>

        <section class="learning-panel">
          <h2>优先复习</h2>
          <p>按近 15 天的答错次数排序，列出最多三个已标注知识点。</p>
          <p v-if="!priorities.length">近 15 天暂无已标注知识点的错题，可继续自测积累记录。</p>
          <ul v-else class="learning-priorities">
            <li v-for="point in priorities" :key="pointKey(point)">
              <h3>{{ point.title }}</h3>
              <p>近 15 天作答 {{ point.recent_attempts }} 次，答错 {{ point.recent_wrong }} 次。</p>
              <p>先通过 AI 答疑梳理易混概念，再做专项自测。复测后回到本页查看正确率变化。</p>
              <div class="learning-actions">
                <RouterLink
                  :to="{
                    path: '/conversation',
                    query: { review: point.title }
                  }"
                  >AI 答疑</RouterLink
                >
                <RouterLink
                  :to="{
                    path: '/exercises',
                    query: { chapter: point.chapter || undefined, topic: point.title }
                  }"
                  >专项自测</RouterLink
                >
              </div>
            </li>
          </ul>
        </section>

        <section class="learning-panel">
          <h2>知识点作答对比</h2>
          <p>正确率按提交次数计算。题目难度和作答数量可能不同，建议结合错题判断复习效果。</p>
          <div class="learning-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">知识点</th>
                  <th scope="col">近 30 天作答</th>
                  <th scope="col">前 15 天正确率</th>
                  <th scope="col">近 15 天正确率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="point in points" :key="pointKey(point)">
                  <th scope="row">{{ point.title || '未分类' }}</th>
                  <td>{{ point.attempts }} 次（错 {{ point.wrong }} 次）</td>
                  <td>
                    {{
                      accuracy(
                        point.attempts - point.recent_attempts,
                        point.wrong - point.recent_wrong
                      )
                    }}
                  </td>
                  <td>{{ accuracy(point.recent_attempts, point.recent_wrong) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import CourseTopbar from '@/components/course/CourseTopbar.vue'
import CoursePageHero from '@/components/course/CoursePageHero.vue'
import { getPersonalLearningAnalysis } from '@/apis/courseApi'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(true)
const error = ref(false)
const points = ref([])
const attemptCount = computed(() => points.value.reduce((sum, point) => sum + point.attempts, 0))
const wrongCount = computed(() => points.value.reduce((sum, point) => sum + point.wrong, 0))
const priorities = computed(() =>
  points.value
    .filter((point) => point.title?.trim() && point.recent_wrong > 0)
    .sort((a, b) => b.recent_wrong - a.recent_wrong)
    .slice(0, 3)
)

function pointKey(point) {
  return JSON.stringify([point.chapter, point.title])
}

function accuracy(total, wrong) {
  return total ? `${Math.round(((total - wrong) / total) * 100)}%` : '暂无作答'
}

async function loadAnalysis() {
  loading.value = true
  error.value = false
  try {
    const result = await getPersonalLearningAnalysis()
    points.value = result.knowledge_points
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadAnalysis)
</script>

<style scoped lang="less">
.personal-learning {
  padding-bottom: 32px;
  color: var(--text-primary);
}

.learning-panel {
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--surface-panel);
}

.learning-panel p,
.learning-panel dt {
  color: var(--text-secondary);
}

.learning-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 0;

  dd {
    margin: 4px 0 0;
    font-size: 24px;
    font-weight: 650;
  }
}

.learning-priorities {
  list-style: none;
  margin: 0;
  padding: 0;

  li {
    padding: 16px 0;
    border-top: 1px solid var(--border-subtle);
  }
}

.learning-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.learning-table {
  overflow-x: auto;

  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
  }

  th,
  td {
    min-width: 100px;
    padding: 10px;
    border-bottom: 1px solid var(--border-subtle);
  }
}
</style>
