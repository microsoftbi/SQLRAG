import { createRouter, createWebHistory } from 'vue-router'
import GraphDB from '../views/GraphDB.vue'
import VectorDB from '../views/VectorDB.vue'
import Debug from '../views/Debug.vue'

const routes = [
  { path: '/', redirect: '/graph' },
  { path: '/graph', component: GraphDB },
  { path: '/vector', component: VectorDB },
  { path: '/debug', component: Debug }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
