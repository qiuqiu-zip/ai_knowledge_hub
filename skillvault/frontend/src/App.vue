<template>
  <el-container style="min-height: 100vh">
    <el-aside width="220px">
      <el-menu router default-active="/">
        <el-menu-item index="/">Dashboard</el-menu-item>
        <el-menu-item index="/sources">Sources</el-menu-item>
        <el-menu-item index="/github">GitHub Import</el-menu-item>
        <el-menu-item index="/documents">Documents</el-menu-item>
        <el-menu-item index="/knowledge">Knowledge</el-menu-item>
        <el-menu-item index="/skill-candidates">Skill Candidates</el-menu-item>
        <el-menu-item index="/skills">Skills</el-menu-item>
        <el-menu-item index="/prompts">Prompts</el-menu-item>
        <el-menu-item index="/search">Search/RAG</el-menu-item>
        <el-menu-item index="/jobs">Jobs</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>
