<template>
  <el-container style="height: 100vh">
    <el-header style="background-color: #409EFF; color: white; display: flex; align-items: center">
      <h1 style="margin: 0">SQLRAG 系统</h1>
    </el-header>
    <el-container>
      <el-aside width="200px" style="background-color: #f5f7fa; padding-top: 20px">
        <el-menu router mode="vertical" :default-active="$route.path">
          <el-menu-item index="/graph">
            <el-icon><data-line /></el-icon>
            <span>GraphDB</span>
          </el-menu-item>
          <el-menu-item index="/vector">
            <el-icon><document /></el-icon>
            <span>VectorDB</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { Document, DataLine } from '@element-plus/icons-vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: Arial, sans-serif;
}
</style>
