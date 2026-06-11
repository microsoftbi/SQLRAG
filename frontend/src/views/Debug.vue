<template>
  <div style="padding: 20px">
    <h2>🛠️ Debug 调试</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="SQL" name="sql">
        <el-input
          v-model="sqlText"
          type="textarea"
          :rows="8"
          placeholder="输入 SQL 语句..."
          style="margin-bottom: 12px; font-family: monospace"
        />
        <el-button type="primary" @click="executeSql" :loading="sqlLoading">
          执行
        </el-button>

        <div v-if="sqlResult !== null" style="margin-top: 16px">
          <el-divider />

          <div v-if="sqlResult.success">
            <p style="color: #67c23a">
              查询成功，共 {{ sqlResult.row_count }} 条记录
            </p>
            <el-table
              :data="sqlResult.rows"
              border
              stripe
              style="width: 100%; margin-top: 8px"
              max-height="500"
              size="small"
            >
              <el-table-column
                v-for="col in sqlResult.columns"
                :key="col"
                :prop="col"
                :label="col"
                min-width="120"
              />
            </el-table>
          </div>
          <div v-else>
            <p style="color: #f56c6c">
              <strong>执行失败:</strong> {{ sqlResult.error }}
            </p>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="提示词" name="prompt">
        <el-input
          v-model="promptText"
          type="textarea"
          :rows="8"
          placeholder="输入提示词..."
          style="margin-bottom: 12px; font-family: monospace"
        />
        <el-button type="primary" @click="callLlm" :loading="llmLoading">
          调用 LLM
        </el-button>

        <div v-if="llmResult !== null" style="margin-top: 16px">
          <el-divider />

          <div v-if="llmResult.success">
            <p style="color: #67c23a">LLM 响应:</p>
            <el-input
              :model-value="llmResult.response"
              type="textarea"
              :rows="10"
              readonly
              style="margin-top: 8px; font-family: monospace"
            />
          </div>
          <div v-else>
            <p style="color: #f56c6c">
              <strong>调用失败:</strong> {{ llmResult.error }}
            </p>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:8798'

const activeTab = ref('sql')
const sqlText = ref('')
const promptText = ref('')
const sqlLoading = ref(false)
const llmLoading = ref(false)
const sqlResult = ref(null)
const llmResult = ref(null)

async function executeSql() {
  if (!sqlText.value.trim()) return
  sqlLoading.value = true
  sqlResult.value = null
  try {
    const res = await axios.post(`${API_BASE}/debug/execute-sql`, {
      sql: sqlText.value,
    })
    sqlResult.value = res.data
  } catch (e) {
    sqlResult.value = { success: false, error: e.message }
  } finally {
    sqlLoading.value = false
  }
}

async function callLlm() {
  if (!promptText.value.trim()) return
  llmLoading.value = true
  llmResult.value = null
  try {
    const res = await axios.post(`${API_BASE}/debug/call-llm`, {
      prompt: promptText.value,
    })
    llmResult.value = res.data
  } catch (e) {
    llmResult.value = { success: false, error: e.message }
  } finally {
    llmLoading.value = false
  }
}
</script>

<style scoped>
.el-tabs {
  margin-top: 16px;
}
.el-divider {
  margin: 8px 0;
}
</style>