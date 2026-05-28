<template>
  <div>
    <!-- 标签页切换 -->
    <div class="tabs">
      <button 
        :class="['tab-btn', { active: activeTab === 'panorama' }]" 
        @click="activeTab = 'panorama'"
      >
        🌐 全景
      </button>
      <button 
        :class="['tab-btn', { active: activeTab === 'qa' }]" 
        @click="activeTab = 'qa'"
      >
        💬 QA
      </button>
    </div>

    <!-- 全景视图 -->
    <div v-if="activeTab === 'panorama'">
      <h2>GraphDB - 知识图谱 ({{ nodesCount }} nodes, {{ edgesCount }} edges)</h2>
      <div ref="networkContainer" style="width: 100%; height: 700px; border: 1px solid #ddd; margin-top: 20px"></div>
      
      <!-- 子图弹窗 -->
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>{{ selectedNodeLabel }} 的关联关系</h3>
            <button class="close-btn" @click="closeModal">×</button>
          </div>
          <div class="modal-body">
            <div class="depth-control">
              <label for="depth-slider">显示深度: {{ depthLevel }} 层</label>
              <input 
                type="range" 
                id="depth-slider" 
                v-model.number="depthLevel" 
                min="1" 
                max="5" 
                step="1"
                @input="updateSubGraph"
              />
              <div class="depth-labels">
                <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
              </div>
            </div>
            <div ref="subNetworkContainer" style="width: 100%; height: 400px; border: 1px solid #eee; margin-top: 20px"></div>
            <div class="stats">
              <span>关联节点: {{ subNodesCount }}</span>
              <span>关联边: {{ subEdgesCount }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- QA视图 -->
    <div v-if="activeTab === 'qa'">
      <h2>💬 知识图谱问答</h2>
      <div class="qa-container">
        <div class="question-section">
          <label for="question-input">请输入问题:</label>
          <textarea 
            id="question-input" 
            v-model="question" 
            placeholder="例如: 方超和周荣是什么关系？&#10;谁认识方超，同时又和周荣有关系？&#10;叶剑遇害案涉及哪些人物？"
            rows="3"
          ></textarea>
          <div class="qa-options">
            <label>
              <input type="checkbox" v-model="useLlm" />
              使用AI生成SQL查询（需配置LLM_API_KEY）
            </label>
          </div>
          <button class="ask-btn" @click="askQuestion" :disabled="!question.trim() || isLoading">
            {{ isLoading ? '思考中...' : '提问' }}
          </button>
        </div>
        
        <div v-if="generatedSql" class="sql-section">
          <label>生成的SQL:</label>
          <div class="sql-box">
            <pre>{{ generatedSql }}</pre>
          </div>
        </div>
        
        <div class="answer-section">
          <label>回答:</label>
          <div class="answer-box">
            <div v-if="isLoading" class="loading">
              <span class="spinner"></span>
              <span>正在分析问题...</span>
            </div>
            <div v-else-if="answer" class="answer-content">
              <pre>{{ answer }}</pre>
            </div>
            <div v-else class="placeholder">
              请在上方输入框中提出您的问题
            </div>
          </div>
        </div>

        <div class="examples">
          <label>示例问题:</label>
          <div class="example-list">
            <button v-for="(ex, index) in exampleQuestions" :key="index" @click="selectExample(ex)">
              {{ ex }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

const activeTab = ref('panorama')
const networkContainer = ref(null)
const subNetworkContainer = ref(null)
const nodesData = ref([])
const edgesData = ref([])
const showModal = ref(false)
const selectedNode = ref(null)
const selectedNodeLabel = ref('')
const depthLevel = ref(1)
const subNodesData = ref([])
const subEdgesData = ref([])
let subNetwork = null

// QA相关
const question = ref('')
const answer = ref('')
const isLoading = ref(false)
const useLlm = ref(false)
const generatedSql = ref('')

const exampleQuestions = [
  '方超和周荣是什么关系？',
  '谁认识方超，同时又和周荣有关系？',
  '叶剑遇害案涉及哪些人物？',
  '从张一昂到霍正之间有哪些关联路径？',
  '哪些人物同时出现在多个案件中？'
]

const nodesCount = computed(() => nodesData.value.length)
const edgesCount = computed(() => edgesData.value.length)
const subNodesCount = computed(() => subNodesData.value.length)
const subEdgesCount = computed(() => subEdgesData.value.length)

const nodeColors = {
  Person: '#409EFF',
  Case: '#67C23A',
  Organization: '#E6A23C',
  Location: '#F56C6C',
  Item: '#909399',
  Event: '#9B59B6'
}

const getNodeLabel = (node) => {
  const data = node.data
  if (node.type === 'Person') return data.name || ''
  if (node.type === 'Case') return data.name || ''
  if (node.type === 'Organization') return data.name || ''
  if (node.type === 'Location') return data.name || ''
  if (node.type === 'Item') return data.name || ''
  if (node.type === 'Event') return data.name || ''
  return ''
}

const findRelatedNodes = (centerNodeId, depth) => {
  const relatedNodeIds = new Set([centerNodeId])
  const relatedEdges = []
  const visited = new Set([centerNodeId])
  
  for (let d = 0; d < depth; d++) {
    const currentLevel = [...visited]
    for (const nodeId of currentLevel) {
      for (const edge of edgesData.value) {
        if (edge.from === nodeId && !visited.has(edge.to)) {
          relatedNodeIds.add(edge.to)
          relatedEdges.push(edge)
          visited.add(edge.to)
        }
        if (edge.to === nodeId && !visited.has(edge.from)) {
          relatedNodeIds.add(edge.from)
          relatedEdges.push(edge)
          visited.add(edge.from)
        }
      }
    }
  }
  
  const relatedNodes = nodesData.value.filter(node => relatedNodeIds.has(node.id))
  return { nodes: relatedNodes, edges: relatedEdges }
}

const updateSubGraph = () => {
  if (!selectedNode.value || !showModal.value || !subNetworkContainer.value) return
  
  const { nodes, edges } = findRelatedNodes(selectedNode.value, depthLevel.value)
  
  subNodesData.value = nodes.map(node => ({
    id: node.id,
    label: getNodeLabel(node),
    color: node.id === selectedNode.value ? '#FF6B6B' : nodeColors[node.type] || '#409EFF',
    title: JSON.stringify(node.data, null, 2),
    shape: node.id === selectedNode.value ? 'star' : 'dot',
    size: node.id === selectedNode.value ? 35 : 25,
    font: { size: 14 }
  }))
  
  subEdgesData.value = edges.map(edge => ({
    id: edge.id,
    from: edge.from,
    to: edge.to,
    label: edge.type,
    arrows: 'to',
    smooth: { type: 'continuous' },
    font: { size: 12 }
  }))
  
  if (subNetwork) {
    subNetwork.destroy()
  }
  
  const subNodes = new DataSet(subNodesData.value)
  const subEdges = new DataSet(subEdgesData.value)
  
  const options = {
    nodes: {
      shape: 'dot',
      size: 25,
      font: { size: 14 },
      borderWidth: 2,
      shadow: true
    },
    edges: {
      font: { size: 12 },
      smooth: { type: 'continuous' },
      arrows: { to: { enabled: true, scaleFactor: 0.8 } },
      color: { inherit: 'from' },
      width: 2
    },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -3000,
        centralGravity: 0.5,
        springLength: 150,
        springConstant: 0.05,
        damping: 0.09,
        avoidOverlap: 0.2
      },
      stabilization: {
        enabled: true,
        iterations: 500
      }
    },
    layout: {
      improvedLayout: true
    },
    interaction: {
      hover: true,
      tooltipDelay: 200
    }
  }
  
  subNetwork = new Network(subNetworkContainer.value, { nodes: subNodes, edges: subEdges }, options)
}

const handleNodeClick = (params) => {
  if (params.nodes.length > 0) {
    const nodeId = params.nodes[0]
    const node = nodesData.value.find(n => n.id === nodeId)
    if (node) {
      selectedNode.value = nodeId
      selectedNodeLabel.value = getNodeLabel(node)
      depthLevel.value = 1
      showModal.value = true
      nextTick(() => {
        updateSubGraph()
      })
    }
  }
}

const closeModal = () => {
  showModal.value = false
  selectedNode.value = null
  selectedNodeLabel.value = ''
  depthLevel.value = 1
  subNodesData.value = []
  subEdgesData.value = []
  if (subNetwork) {
    subNetwork.destroy()
    subNetwork = null
  }
}

const selectExample = (ex) => {
  question.value = ex
}

const askQuestion = async () => {
  if (!question.value.trim()) return
  
  isLoading.value = true
  answer.value = ''
  generatedSql.value = ''
  
  try {
    const response = await axios.post('http://localhost:8798/graph/qa', {
      question: question.value,
      use_llm: useLlm.value
    })
    answer.value = response.data.answer
    if (response.data.generated_sql) {
      generatedSql.value = response.data.generated_sql
    }
  } catch (error) {
    console.error('QA request failed:', error)
    answer.value = '抱歉，暂时无法回答这个问题。'
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await axios.get('http://localhost:8798/graph/data')
    console.log('Graph data loaded:', res.data)
    
    nodesData.value = res.data.nodes.map(node => ({
      id: node.id,
      label: getNodeLabel(node),
      color: nodeColors[node.type] || '#409EFF',
      title: JSON.stringify(node.data, null, 2),
      shape: 'dot',
      size: 25,
      font: { size: 14 },
      type: node.type,
      data: node.data
    }))
    
    edgesData.value = res.data.edges.map(edge => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      type: edge.type
    }))
    
    console.log('Nodes prepared:', nodesData.value.length)
    console.log('Edges prepared:', edgesData.value.length)
    
    const nodes = new DataSet(nodesData.value)
    const edges = new DataSet(edgesData.value)
    const data = { nodes, edges }

    const options = {
      nodes: {
        shape: 'dot',
        size: 25,
        font: { size: 14 },
        borderWidth: 2,
        shadow: true
      },
      edges: {
        font: { size: 12 },
        smooth: { type: 'continuous' },
        arrows: { to: { enabled: true, scaleFactor: 0.8 } },
        color: { inherit: 'from' },
        width: 2
      },
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -4000,
          centralGravity: 0.3,
          springLength: 200,
          springConstant: 0.04,
          damping: 0.09,
          avoidOverlap: 0.1
        },
        stabilization: {
          enabled: true,
          iterations: 1000
        }
      },
      layout: {
        improvedLayout: true
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: false,
        hideNodesOnDrag: false
      }
    }

    const network = new Network(networkContainer.value, data, options)
    network.on('click', handleNodeClick)
  } catch (error) {
    console.error('Error loading graph data:', error)
  }
})

watch(depthLevel, () => {
  if (showModal.value && selectedNode.value) {
    updateSubGraph()
  }
})

onUnmounted(() => {
  if (subNetwork) {
    subNetwork.destroy()
  }
})
</script>

<style scoped>
.tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
}

.tab-btn {
  padding: 10px 24px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #f5f5f5;
  color: #666;
}

.tab-btn:hover {
  background: #e8e8e8;
}

.tab-btn.active {
  background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.qa-container {
  max-width: 900px;
  margin: 0 auto;
}

.question-section {
  margin-bottom: 24px;
}

.question-section label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.question-section textarea {
  width: 100%;
  padding: 12px 16px;
  font-size: 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  resize: vertical;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

.question-section textarea:focus {
  outline: none;
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.ask-btn {
  display: block;
  margin-top: 12px;
  padding: 10px 32px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.ask-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.4);
}

.ask-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.qa-options {
  margin-top: 12px;
  padding: 8px 0;
}

.qa-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
}

.qa-options input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.sql-section {
  margin-bottom: 24px;
}

.sql-section label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.sql-box {
  padding: 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #1e1e1e;
  max-height: 300px;
  overflow-y: auto;
}

.sql-box pre {
  margin: 0;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13px;
  color: #d4d4d4;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.answer-section {
  margin-bottom: 24px;
}

.answer-section label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.answer-box {
  min-height: 200px;
  padding: 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #fafafa;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 12px;
  color: #409EFF;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #409EFF;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.answer-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  font-size: 14px;
  color: #333;
  line-height: 1.8;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 168px;
  color: #999;
  font-style: italic;
}

.examples {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
}

.examples label {
  display: block;
  font-weight: 600;
  margin-bottom: 12px;
  color: #666;
}

.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-list button {
  padding: 8px 16px;
  font-size: 13px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.example-list button:hover {
  background: #409EFF;
  color: white;
  border-color: #409EFF;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 900px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.modal-body {
  padding: 20px;
}

.depth-control {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
}

.depth-control label {
  font-weight: 600;
  color: #666;
}

.depth-control input[type="range"] {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: linear-gradient(90deg, #409EFF 0%, #67C23A 100%);
  border-radius: 3px;
  cursor: pointer;
}

.depth-control input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: white;
  border: 3px solid #409EFF;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.depth-control input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.depth-labels {
  display: flex;
  justify-content: space-between;
  color: #999;
  font-size: 12px;
}

.stats {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
  margin-top: 12px;
  color: #666;
  font-size: 14px;
}

.stats span {
  background: #e9ecef;
  padding: 6px 12px;
  border-radius: 20px;
}
</style>