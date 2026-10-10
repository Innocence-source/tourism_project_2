<template>
    <!-- 根组件只承载路由出口，具体布局在 views/Dashboard.vue -->
    <router-view/>
</template>

<script setup>
/**
 * 根组件
 * =======
 * 全局样式（重置、底色、字体、滚动条）写在本文件的非 scoped style 中，
 * 保证所有子组件都能继承；组件私有样式则在各组件内用 <style scoped>。
 */
</script>

<style>
/* ==================== 全局重置 ==================== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html,
body,
#app {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

body {
    /* 深蓝科技风底色，与设计稿一致 */
    background: #0b1a3a;
    color: #ffffff;
    font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* 大屏场景不需要文本选中，避免拖拽时出现蓝色选区 */
body {
    user-select: none;
}

/* 隐藏滚动条（大屏内容应完整落在 1920x1080 内） */
::-webkit-scrollbar {
    width: 0;
    height: 0;
}
</style>
