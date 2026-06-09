<template>
  <div>
    <h2>VectorDB - 向量数据库</h2>
    <el-tabs v-model="activeTab" style="margin-top: 20px">
      <el-tab-pane label="文档" name="documents">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>文档管理</span>
              <div style="display: flex; gap: 12px; align-items: center">
                <el-select v-model="selectedKB" placeholder="全部知识库" clearable style="width: 200px" @change="loadDocuments">
                  <el-option label="全部知识库" :value="null" />
                  <el-option v-for="kb in knowledgeBases" :key="kb.KnowledgeBaseId" :label="kb.Name" :value="kb.KnowledgeBaseId" />
                </el-select>
              </div>
            </div>
          </template>
          <el-table :data="documents" border style="width: 100%">
            <el-table-column prop="DocumentId" label="ID" width="80" />
            <el-table-column prop="Title" label="标题" />
            <el-table-column prop="KnowledgeBaseName" label="所属知识库" width="180">
              <template #default="{ row }">
                <template v-if="editingDocId === row.DocumentId">
                  <el-select v-model="editDocKB" size="small" style="width: 130px" placeholder="不归属" clearable>
                    <el-option v-for="kb in knowledgeBases" :key="kb.KnowledgeBaseId" :label="kb.Name" :value="kb.KnowledgeBaseId" />
                  </el-select>
                  <el-button link type="primary" size="small" @click="saveDocKB(row)" style="margin-left: 2px">保存</el-button>
                  <el-button link size="small" @click="editingDocId = null">取消</el-button>
                </template>
                <template v-else>
                  <span style="cursor: pointer; border-bottom: 1px dashed #ccc" @click="startEditDocKB(row)" :title="'点击修改知识库'">{{ row.KnowledgeBaseName || '-' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="Source" label="来源" width="200" />
            <el-table-column prop="CreatedAt" label="创建时间" width="200" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="showChunks(row)">查看分块</el-button>
                <el-popconfirm
                  title="确定删除该文档及其所有分块和向量数据？"
                  confirm-button-text="确定删除"
                  @confirm="deleteDocument(row)"
                >
                  <template #reference>
                    <el-button link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
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
            <el-form-item label="知识库">
              <el-select v-model="newDoc.knowledge_base_id" placeholder="不归属" clearable style="width: 100%">
                <el-option v-for="kb in knowledgeBases" :key="kb.KnowledgeBaseId" :label="kb.Name" :value="kb.KnowledgeBaseId" />
              </el-select>
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
          <div style="display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap">
            <el-upload
              drag
              action="#"
              :show-file-list="false"
              :before-upload="handleFileUpload"
              :loading="uploadLoading"
              style="text-align: center; flex-shrink: 0"
            >
              <el-icon class="el-icon--upload" style="font-size: 48px; color: #409eff"><UploadFilled /></el-icon>
              <div style="margin-top: 16px; font-size: 16px; color: #606266">
                将文件拖到此处，或<em style="color: #409eff">点击上传</em>
              </div>
              <div style="margin-top: 8px; font-size: 12px; color: #909399">
                支持 .txt, .md, .docx, .pdf 等格式
              </div>
            </el-upload>
            <div style="display: flex; flex-direction: column; gap: 8px; min-width: 200px">
              <el-select v-model="uploadKB" placeholder="选择知识库（可选）" clearable style="width: 200px">
                <el-option v-for="kb in knowledgeBases" :key="kb.KnowledgeBaseId" :label="kb.Name" :value="kb.KnowledgeBaseId" />
              </el-select>
              <div v-if="currentUpload" style="font-size: 13px; color: #606266">
                已上传：<strong>{{ currentUpload.name }}</strong>
                （{{ formatFileSize(currentUpload.size) }}）
              </div>
            </div>
          </div>

          <el-tabs v-model="chunkMethodTab" style="margin-top: 16px">
            <el-tab-pane label="固定分块" name="fixed">
              <div style="display: flex; gap: 24px; align-items: center; padding: 8px 0; flex-wrap: wrap">
                <div>
                  <span style="font-size: 13px; margin-right: 8px">Chunk Size：</span>
                  <el-input-number v-model="uploadChunkSize" :min="100" :max="5000" :step="100" size="small" style="width: 130px" controls-position="right" />
                </div>
                <div>
                  <span style="font-size: 13px; margin-right: 8px">Chunk Overlap：</span>
                  <el-input-number v-model="uploadChunkOverlap" :min="0" :max="1000" :step="50" size="small" style="width: 120px" controls-position="right" />
                </div>
                <el-button type="primary" size="small" @click="previewFixedChunks" :disabled="!currentUpload" :loading="previewLoading">分块预览</el-button>
              </div>

              <!-- 双栏预览区域 -->
              <div v-if="currentUpload" style="display: flex; gap: 16px; min-height: 400px; margin-top: 8px">
                <div style="flex: 1; border: 1px solid #dcdfe6; border-radius: 4px; display: flex; flex-direction: column">
                  <div style="background: #f5f7fa; padding: 8px 12px; font-weight: bold; border-bottom: 1px solid #dcdfe6">
                    原文
                    <span style="font-weight: normal; font-size: 12px; color: #909399; margin-left: 8px">{{ currentUpload.name }}</span>
                  </div>
                  <div style="padding: 12px; overflow-y: auto; white-space: pre-wrap; font-size: 13px; flex: 1; max-height: 500px">{{ currentUploadContent }}</div>
                </div>
                <div style="flex: 1; border: 1px solid #dcdfe6; border-radius: 4px; display: flex; flex-direction: column">
                  <div style="background: #f5f7fa; padding: 8px 12px; font-weight: bold; border-bottom: 1px solid #dcdfe6">
                    分块结果
                    <span v-if="fixedPreviewChunks.length > 0" style="font-weight: normal; font-size: 12px; color: #909399; margin-left: 8px">共 {{ fixedPreviewChunks.length }} 块</span>
                    <el-button type="primary" size="small" style="float: right" @click="commitFixedChunks" :loading="fixedCommitting" :disabled="fixedPreviewChunks.length === 0">文档入库</el-button>
                  </div>
                  <div style="padding: 12px; overflow-y: auto; flex: 1; max-height: 500px">
                    <div v-if="fixedPreviewChunks.length === 0 && !previewLoading" style="padding: 40px 0; text-align: center; color: #909399; font-size: 14px">
                      点击「分块预览」查看分块结果
                    </div>
                    <div v-if="previewLoading" style="padding: 40px 0; text-align: center; color: #909399; font-size: 14px">
                      分块计算中...
                    </div>
                    <div v-for="(chunk, idx) in fixedPreviewChunks" :key="idx" style="margin-bottom: 12px; padding: 8px; background: #f0f9ff; border-radius: 4px; border-left: 3px solid #409eff">
                      <div style="font-size: 12px; color: #909399; margin-bottom: 4px">#{{ idx + 1 }}（长度：{{ chunk.Length }}）</div>
                      <div style="font-size: 13px; white-space: pre-wrap">{{ chunk.ChunkText }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else style="padding: 40px 0; text-align: center; color: #909399; font-size: 14px">
                请先上传文档
              </div>
            </el-tab-pane>
            <el-tab-pane label="语义分块" name="semantic">
              <div style="padding: 8px 0">
                <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap">
                  <el-select v-model="semanticDocId" placeholder="选择已上传的文档" style="width: 300px">
                    <el-option v-for="f in uploadedFiles" :key="f.documentId" :label="f.name" :value="f.documentId" />
                  </el-select>
                  <el-button type="primary" @click="startSemanticChunk" :loading="semanticLoading" :disabled="!semanticDocId">开始语义分块</el-button>
                </div>
                <div v-if="semanticResult" style="display: flex; gap: 16px; min-height: 400px">
                  <div style="flex: 1; border: 1px solid #dcdfe6; border-radius: 4px; display: flex; flex-direction: column">
                    <div style="background: #f5f7fa; padding: 8px 12px; font-weight: bold; border-bottom: 1px solid #dcdfe6">原文</div>
                    <div style="padding: 12px; overflow-y: auto; white-space: pre-wrap; font-size: 13px; flex: 1; max-height: 500px">{{ semanticResult.original }}</div>
                  </div>
                  <div style="flex: 1; border: 1px solid #dcdfe6; border-radius: 4px; display: flex; flex-direction: column">
                    <div style="background: #f5f7fa; padding: 8px 12px; font-weight: bold; border-bottom: 1px solid #dcdfe6">
                      分块结果（共 {{ semanticResult.chunks.length }} 块）
                      <el-button type="primary" size="small" style="float: right" @click="commitSemanticChunks" :loading="semanticCommitting">文档入库</el-button>
                    </div>
                    <div style="padding: 12px; overflow-y: auto; flex: 1; max-height: 500px">
                      <div v-for="(chunk, idx) in semanticResult.chunks" :key="idx" style="margin-bottom: 12px; padding: 8px; background: #f0f9ff; border-radius: 4px; border-left: 3px solid #409eff">
                        <div style="font-size: 12px; color: #909399; margin-bottom: 4px">#{{ idx + 1 }}（长度：{{ chunk.Length }}）</div>
                        <div style="font-size: 13px; white-space: pre-wrap">{{ chunk.ChunkText }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else-if="!semanticLoading" style="padding: 40px 0; text-align: center; color: #909399; font-size: 14px">
                  请先上传文档，然后选择一个文档开始语义分块
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
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

      <el-tab-pane label="知识库" name="knowledge">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>知识库列表</span>
              <el-button type="primary" size="small" @click="showCreateKBDialog = true">创建知识库</el-button>
            </div>
          </template>
          <el-table :data="knowledgeBases" border style="width: 100%">
            <el-table-column prop="KnowledgeBaseId" label="ID" width="80" />
            <el-table-column prop="Name" label="名称" />
            <el-table-column prop="Description" label="描述" min-width="200">
              <template #default="{ row }">
                <span>{{ row.Description || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="CreatedAt" label="创建时间" width="200" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="editKB(row)">编辑</el-button>
                <el-popconfirm
                  title="确定删除该知识库？关联文档将解除所属关系。"
                  confirm-button-text="确定删除"
                  @confirm="deleteKB(row)"
                >
                  <template #reference>
                    <el-button link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 创建知识库 Dialog -->
        <el-dialog v-model="showCreateKBDialog" title="创建知识库" width="40%">
          <el-form :model="kbForm" label-width="80px">
            <el-form-item label="名称">
              <el-input v-model="kbForm.name" placeholder="请输入知识库名称" />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="kbForm.description" type="textarea" :rows="3" placeholder="可选" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showCreateKBDialog = false">取消</el-button>
            <el-button type="primary" @click="createKB">确定</el-button>
          </template>
        </el-dialog>

        <!-- 编辑知识库 Dialog -->
        <el-dialog v-model="showEditKBDialog" :title="`编辑知识库 - ${editingKB?.Name || ''}`" width="40%">
          <el-form :model="kbEditForm" label-width="80px">
            <el-form-item label="名称">
              <el-input v-model="kbEditForm.name" placeholder="请输入知识库名称" />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="kbEditForm.description" type="textarea" :rows="3" placeholder="可选" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showEditKBDialog = false">取消</el-button>
            <el-button type="primary" @click="updateKB">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="配置" name="config">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统配置</span>
              <el-button type="primary" size="small" @click="saveConfig" :loading="configSaving">保存配置</el-button>
            </div>
          </template>
          <el-form :model="config" label-width="180px" style="max-width: 600px">
            <el-form-item label="Chunk Size（分块大小）">
              <el-input-number v-model="config.chunk_size" :min="100" :max="5000" :step="100" />
              <div style="color: #909399; font-size: 12px; margin-top: 4px">每个文本块的最大字符数</div>
            </el-form-item>
            <el-form-item label="Chunk Overlap（分块重叠）">
              <el-input-number v-model="config.chunk_overlap" :min="0" :max="1000" :step="50" />
              <div style="color: #909399; font-size: 12px; margin-top: 4px">相邻文本块之间的重叠字符数</div>
            </el-form-item>
            <el-form-item label="Embedding Model（嵌入模型）">
              <el-input v-model="config.embedding_model" placeholder="bge-m3" />
              <div style="color: #909399; font-size: 12px; margin-top: 4px">Ollama 上的文本嵌入模型名称</div>
            </el-form-item>
          </el-form>
          <el-alert
            v-if="configMessage"
            :title="configMessage"
            :type="configMessageType"
            show-icon
            :closable="true"
            @close="configMessage = ''"
            style="margin-top: 16px"
          />
        </el-card>
      </el-tab-pane>
      <!-- 索引管理 -->
      <el-tab-pane label="索引管理" name="index">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>向量索引管理</span>
            </div>
          </template>
          <div style="display: flex; gap: 16px; flex-wrap: wrap">
            <el-button type="success" @click="handleCreateIndex" :loading="indexLoading">
              创建索引
            </el-button>
            <el-button type="danger" @click="handleDropIndex" :loading="indexLoading">
              删除索引
            </el-button>
          </div>
          <el-alert
            v-if="indexMessage"
            :title="indexMessage"
            :type="indexMessageType"
            show-icon
            :closable="true"
            @close="indexMessage = ''"
            style="margin-top: 16px"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('documents')
const documents = ref([])
const showAddDialog = ref(false)
const newDoc = ref({ title: '', content: '', source: '', knowledge_base_id: null })
const showChunksDialog = ref(false)
const currentDocument = ref(null)
const currentChunks = ref([])
const uploadLoading = ref(false)
const uploadedFiles = ref([])
const question = ref('')
const answer = ref('')
const sources = ref([])
const loading = ref(false)
const knowledgeBases = ref([])
const selectedKB = ref(null)
const uploadKB = ref(null)
const chunkMethodTab = ref('fixed')
const uploadChunkSize = ref(500)
const uploadChunkOverlap = ref(100)
const semanticDocId = ref(null)
const semanticLoading = ref(false)
const semanticResult = ref(null)
const semanticCommitting = ref(false)
const showCreateKBDialog = ref(false)
const showEditKBDialog = ref(false)
const editingKB = ref(null)
const kbForm = ref({ name: '', description: '' })
const kbEditForm = ref({ name: '', description: '' })
const editingDocId = ref(null)
const editDocKB = ref(null)
const showPreviewDialog = ref(false)
const previewChunks = ref([])
const previewChunkSize = ref(0)
const previewChunkOverlap = ref(0)

// 新的上传双栏预览
const currentUpload = ref(null)          // 当前选中的已上传文档 { name, size, documentId }
const currentUploadContent = ref('')     // 当前文档原文内容
const fixedPreviewChunks = ref([])       // 固定分块预览结果
const previewLoading = ref(false)        // 分块预览加载中
const fixedCommitting = ref(false)       // 固定分块入库中

const config = ref({
  chunk_size: 500,
  chunk_overlap: 100,
  embedding_model: 'quentinz/bge-large-zh-v1.5:latest',
})
const configSaving = ref(false)
const configMessage = ref('')
const configMessageType = ref('success')

const loadConfig = async () => {
  try {
    const res = await axios.get('http://localhost:8798/vector/config')
    config.value = res.data
    uploadChunkSize.value = res.data.chunk_size
    uploadChunkOverlap.value = res.data.chunk_overlap
  } catch (error) {
    console.error('Error loading config:', error)
  }
}

const saveConfig = async () => {
  configSaving.value = true
  configMessage.value = ''
  try {
    const res = await axios.put('http://localhost:8798/vector/config', {
      chunk_size: config.value.chunk_size,
      chunk_overlap: config.value.chunk_overlap,
      embedding_model: config.value.embedding_model,
    })
    configMessage.value = res.data.message
    configMessageType.value = 'success'
  } catch (error) {
    console.error('Error saving config:', error)
    configMessage.value = '保存失败: ' + (error.response?.data?.message || error.message)
    configMessageType.value = 'error'
  } finally {
    configSaving.value = false
  }
}

// 索引管理
const indexLoading = ref(false)
const indexMessage = ref('')
const indexMessageType = ref('success')

const handleCreateIndex = async () => {
  indexLoading.value = true
  indexMessage.value = ''
  try {
    const res = await axios.post('http://localhost:8798/vector/index/create')
    indexMessage.value = res.data.message
    indexMessageType.value = 'success'
  } catch (error) {
    indexMessage.value = '创建失败: ' + (error.response?.data?.message || error.message)
    indexMessageType.value = 'error'
  } finally {
    indexLoading.value = false
  }
}

const handleDropIndex = async () => {
  indexLoading.value = true
  indexMessage.value = ''
  try {
    const res = await axios.post('http://localhost:8798/vector/index/drop')
    indexMessage.value = res.data.message
    indexMessageType.value = 'success'
  } catch (error) {
    indexMessage.value = '删除失败: ' + (error.response?.data?.message || error.message)
    indexMessageType.value = 'error'
  } finally {
    indexLoading.value = false
  }
}

const loadDocuments = async () => {
  try {
    const params = {}
    if (selectedKB.value) {
      params.knowledge_base_id = selectedKB.value
    }
    const res = await axios.get('http://localhost:8798/vector/documents', { params })
    documents.value = res.data.documents
  } catch (error) {
    console.error('Error loading documents:', error)
  }
}

const addDocument = async () => {
  try {
    await axios.post('http://localhost:8798/vector/documents', newDoc.value)
    showAddDialog.value = false
    newDoc.value = { title: '', content: '', source: '', knowledge_base_id: null }
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

const deleteDocument = async (doc) => {
  try {
    await axios.delete(`http://localhost:8798/vector/documents/${doc.DocumentId}`)
    ElMessage.success('文档已删除')
    loadDocuments()
  } catch (error) {
    console.error('Error deleting document:', error)
    ElMessage.error('删除失败: ' + (error.response?.data?.message || error.message))
  }
}

const startEditDocKB = (doc) => {
  editingDocId.value = doc.DocumentId
  editDocKB.value = doc.KnowledgeBaseId
}

const saveDocKB = async (doc) => {
  try {
    await axios.put(`http://localhost:8798/vector/documents/${doc.DocumentId}`, {
      knowledge_base_id: editDocKB.value,
    })
    editingDocId.value = null
    ElMessage.success('知识库已更新')
    loadDocuments()
  } catch (error) {
    console.error('Error updating document KB:', error)
    ElMessage.error('更新失败')
  }
}

const handleFileUpload = async (file) => {
  uploadLoading.value = true
  fixedPreviewChunks.value = []
  semanticResult.value = null
  currentUploadContent.value = ''

  const formData = new FormData()
  formData.append('file', file)
  if (uploadKB.value) {
    formData.append('knowledge_base_id', uploadKB.value)
  }

  try {
    const res = await axios.post('http://localhost:8798/vector/documents/upload', formData)
    const docId = res.data.documentId
    // 保存到上传列表中（语义分块用）
    uploadedFiles.value.push({
      name: file.name,
      size: file.size,
      documentId: docId,
    })
    // 设为当前选中文档
    currentUpload.value = { name: file.name, size: file.size, documentId: docId }
    // 加载文档内容
    const contentRes = await axios.get(`http://localhost:8798/vector/documents/${docId}`)
    currentUploadContent.value = contentRes.data.Content || ''
  } catch (error) {
    console.error('Upload failed:', error)
    ElMessage.error('上传失败: ' + (error.response?.data?.message || error.message))
  } finally {
    uploadLoading.value = false
    loadDocuments()
  }
  return false
}

const previewFixedChunks = async () => {
  if (!currentUpload.value) return
  previewLoading.value = true
  try {
    const res = await axios.post(`http://localhost:8798/vector/documents/${currentUpload.value.documentId}/preview-chunks`, {
      chunk_size: uploadChunkSize.value,
      chunk_overlap: uploadChunkOverlap.value,
    })
    fixedPreviewChunks.value = res.data.chunks
  } catch (error) {
    console.error('Error previewing chunks:', error)
    ElMessage.error('分块预览失败: ' + (error.response?.data?.message || error.message))
  } finally {
    previewLoading.value = false
  }
}

const commitFixedChunks = async () => {
  if (!currentUpload.value || fixedPreviewChunks.value.length === 0) return
  fixedCommitting.value = true
  try {
    const res = await axios.post(`http://localhost:8798/vector/documents/${currentUpload.value.documentId}/commit-chunks`, {
      chunk_size: uploadChunkSize.value,
      chunk_overlap: uploadChunkOverlap.value,
    })
    ElMessage.success(res.data.message)
    // 从上传列表中移除
    uploadedFiles.value = uploadedFiles.value.filter(f => f.documentId !== currentUpload.value.documentId)
    currentUpload.value = null
    currentUploadContent.value = ''
    fixedPreviewChunks.value = []
    loadDocuments()
  } catch (error) {
    console.error('Error committing chunks:', error)
    ElMessage.error('入库失败: ' + (error.response?.data?.message || error.message))
  } finally {
    fixedCommitting.value = false
  }
}

const startSemanticChunk = async () => {
  if (!semanticDocId.value) return
  semanticLoading.value = true
  semanticResult.value = null
  try {
    const res = await axios.post(`http://localhost:8798/vector/documents/${semanticDocId.value}/semantic-chunk`)
    semanticResult.value = {
      original: res.data.original_content,
      chunks: res.data.chunks,
    }
  } catch (error) {
    console.error('Error semantic chunking:', error)
    ElMessage.error('语义分块失败: ' + (error.response?.data?.message || error.message))
  } finally {
    semanticLoading.value = false
  }
}

const commitSemanticChunks = async () => {
  if (!semanticDocId.value || !semanticResult.value) return
  semanticCommitting.value = true
  try {
    const chunkTexts = semanticResult.value.chunks.map(c => c.ChunkText)
    const res = await axios.post(`http://localhost:8798/vector/documents/${semanticDocId.value}/commit-chunks-raw`, {
      chunks: chunkTexts,
    })
    ElMessage.success(res.data.message)
    // 从上传列表中移除
    uploadedFiles.value = uploadedFiles.value.filter(f => f.documentId !== semanticDocId.value)
    // 重置语义分块界面
    semanticDocId.value = null
    semanticResult.value = null
    loadDocuments()
  } catch (error) {
    console.error('Error committing semantic chunks:', error)
    ElMessage.error('入库失败: ' + (error.response?.data?.message || error.message))
  } finally {
    semanticCommitting.value = false
  }
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

const loadKnowledgeBases = async () => {
  try {
    const res = await axios.get('http://localhost:8798/vector/knowledge-bases')
    knowledgeBases.value = res.data.knowledge_bases
  } catch (error) {
    console.error('Error loading knowledge bases:', error)
  }
}

const createKB = async () => {
  if (!kbForm.value.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    await axios.post('http://localhost:8798/vector/knowledge-bases', {
      name: kbForm.value.name,
      description: kbForm.value.description,
    })
    showCreateKBDialog.value = false
    kbForm.value = { name: '', description: '' }
    ElMessage.success('知识库已创建')
    loadKnowledgeBases()
  } catch (error) {
    console.error('Error creating knowledge base:', error)
    ElMessage.error('创建失败')
  }
}

const editKB = (kb) => {
  editingKB.value = kb
  kbEditForm.value = { name: kb.Name, description: kb.Description || '' }
  showEditKBDialog.value = true
}

const updateKB = async () => {
  if (!kbEditForm.value.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    await axios.put(`http://localhost:8798/vector/knowledge-bases/${editingKB.value.KnowledgeBaseId}`, {
      name: kbEditForm.value.name,
      description: kbEditForm.value.description,
    })
    showEditKBDialog.value = false
    ElMessage.success('知识库已更新')
    loadKnowledgeBases()
  } catch (error) {
    console.error('Error updating knowledge base:', error)
    ElMessage.error('更新失败')
  }
}

const deleteKB = async (kb) => {
  try {
    await axios.delete(`http://localhost:8798/vector/knowledge-bases/${kb.KnowledgeBaseId}`)
    ElMessage.success('知识库已删除')
    loadKnowledgeBases()
  } catch (error) {
    console.error('Error deleting knowledge base:', error)
    ElMessage.error('删除失败: ' + (error.response?.data?.message || error.message))
  }
}

onMounted(() => {
  loadDocuments()
  loadConfig()
  loadKnowledgeBases()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
