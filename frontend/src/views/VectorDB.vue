<template>
  <div>
    <h2>VectorDB - 向量数据库</h2>
    <el-tabs v-model="activeTab" style="margin-top: 20px">
      <el-tab-pane label="文档" name="documents">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>文档管理</span>
              <el-button type="primary" size="small" @click="showAddDialog = true">添加文档</el-button>
            </div>
          </template>
          <el-table :data="documents" border style="width: 100%">
            <el-table-column prop="DocumentId" label="ID" width="80" />
            <el-table-column prop="Title" label="标题" />
            <el-table-column prop="Source" label="来源" width="200" />
            <el-table-column prop="CreatedAt" label="创建时间" width="200" />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="showChunks(row)">查看分块</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-dialog v-model="showAddDialog" title="添加文档" width="50%">
          <el-form :model="newDoc" label-width="80px">
            <el-form-item label="标题">
              <el-input v-model="newDoc.title" />
            </el-form-item>
            <el-form-item label="内容">
              <el-input v-model="newDoc.content" type="textarea" :rows="10" />
            </el-form-item>
            <el-form-item label="来源">
              <el-input v-model="newDoc.source" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showAddDialog = false">取消</el-button>
            <el-button type="primary" @click="addDocument">确定</el-button>
          </template>
        </el-dialog>

        <el-dialog v-model="showChunksDialog" :title="`${currentDocument?.Title || '文档'} - 分块列表`" width="70%">
          <el-table :data="currentChunks" border>
            <el-table-column prop="ChunkId" label="ID" width="80" />
            <el-table-column prop="ChunkIndex" label="序号" width="100" />
            <el-table-column prop="ChunkText" label="内容">
              <template #default="{ row }">
                <div style="max-height: 150px; overflow-y: auto; white-space: pre-wrap">{{ row.ChunkText }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="CreatedAt" label="创建时间" width="180" />
          </el-table>
          <template #footer>
            <el-button @click="showChunksDialog = false">关闭</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
      
      <el-tab-pane label="文档上传" name="upload">
        <el-card>
          <template #header>
            <span>文档上传</span>
          </template>
          <el-upload
            drag
            action="#"
            :show-file-list="false"
            :before-upload="handleFileUpload"
            :loading="uploadLoading"
            style="text-align: center"
          >
            <el-icon class="el-icon--upload" style="font-size: 48px; color: #409eff"><UploadFilled /></el-icon>
            <div style="margin-top: 16px; font-size: 16px; color: #606266">
              将文件拖到此处，或<em style="color: #409eff">点击上传</em>
            </div>
            <div style="margin-top: 8px; font-size: 12px; color: #909399">
              支持 .txt, .md, .docx, .pdf 等格式
            </div>
          </el-upload>
          
          <div v-if="uploadedFiles.length > 0" style="margin-top: 24px">
            <el-divider content-position="left">已上传文档</el-divider>
            <el-table :data="uploadedFiles" border>
              <el-table-column prop="name" label="文件名" />
              <el-table-column prop="size" label="大小" width="120">
                <template #default="{ row }">
                  {{ formatFileSize(row.size) }}
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'success' ? 'success' : row.status === 'pending' ? 'warning' : 'danger'">
                    {{ row.status === 'success' ? '成功' : row.status === 'pending' ? '处理中...' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="QA" name="qa">
        <el-card>
          <template #header>
            <span>智能问答</span>
          </template>
          <el-form @submit.prevent="askQuestion">
            <el-form-item label="问题">
              <el-input v-model="question" placeholder="请输入您的问题" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="askQuestion" :loading="loading">提问</el-button>
            </el-form-item>
          </el-form>
          
          <div v-if="answer" style="margin-top: 20px">
            <el-divider content-position="left">答案</el-divider>
            <el-card>
              <div v-html="answer"></div>
            </el-card>
            
            <div v-if="sources.length > 0" style="margin-top: 20px">
              <el-divider content-position="left">召回内容</el-divider>
              <el-card>
                <el-timeline>
                  <el-timeline-item v-for="(source, idx) in sources" :key="idx">
                    <div><strong>{{ source.Title || '来源 ' + (idx + 1) }}</strong></div>
                    <div style="color: #666; font-size: 14px; margin-top: 8px; white-space: pre-wrap">{{ source.ChunkText }}</div>
                  </el-timeline-item>
                </el-timeline>
              </el-card>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { UploadFilled } from '@element-plus/icons-vue'

const activeTab = ref('documents')
const documents = ref([])
const showAddDialog = ref(false)
const newDoc = ref({ title: '', content: '', source: '' })
const showChunksDialog = ref(false)
const currentDocument = ref(null)
const currentChunks = ref([])
const uploadLoading = ref(false)
const uploadedFiles = ref([])
const question = ref('')
const answer = ref('')
const sources = ref([])
const loading = ref(false)

const loadDocuments = async () => {
  try {
    const res = await axios.get('http://localhost:8798/vector/documents')
    documents.value = res.data.documents
  } catch (error) {
    console.error('Error loading documents:', error)
  }
}

const addDocument = async () => {
  try {
    await axios.post('http://localhost:8798/vector/documents', newDoc.value)
    showAddDialog.value = false
    newDoc.value = { title: '', content: '', source: '' }
    loadDocuments()
  } catch (error) {
    console.error('Error adding document:', error)
  }
}

const showChunks = async (doc) => {
  currentDocument.value = doc
  showChunksDialog.value = true
  currentChunks.value = []
  
  try {
    const res = await axios.get(`http://localhost:8798/vector/documents/${doc.DocumentId}/chunks`)
    currentChunks.value = res.data.chunks || []
  } catch (error) {
    console.error('Error loading chunks:', error)
  }
}

const handleFileUpload = async (file) => {
  uploadLoading.value = true

  const fileItem = {
    name: file.name,
    size: file.size,
    status: 'pending'
  }
  uploadedFiles.value.push(fileItem)
  const fileIndex = uploadedFiles.value.length - 1

  const formData = new FormData()
  formData.append('file', file)

  try {
    await axios.post('http://localhost:8798/vector/documents/upload', formData)
    uploadedFiles.value[fileIndex].status = 'success'
  } catch (error) {
    console.error('Upload request failed, will retry check after 10s:', error)
    // 等 10 秒后重新加载文档列表，确认是否实际上传成功
    setTimeout(async () => {
      try {
        const res = await axios.get('http://localhost:8798/vector/documents')
        const found = res.data.documents.some(d => d.Title === file.name)
        uploadedFiles.value[fileIndex].status = found ? 'success' : 'error'
      } catch {
        uploadedFiles.value[fileIndex].status = 'error'
      }
    }, 10000)
  } finally {
    uploadLoading.value = false
    loadDocuments()
  }
  return false
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const askQuestion = async () => {
  if (!question.value.trim()) return
  loading.value = true
  answer.value = ''
  sources.value = []
  
  try {
    const res = await axios.post('http://localhost:8798/vector/qa', {
      question: question.value
    })
    answer.value = res.data.answer
    sources.value = res.data.sources || []
  } catch (error) {
    console.error('Error asking question:', error)
    answer.value = '抱歉，处理问题时出错了'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
