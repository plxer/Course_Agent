---
layout: home

hero:
  name: "课程智能体平台"
  text: "面向课程学习的智能问答与伴读系统"
  tagline: 集成课程对话、课本伴读、视频伴读、习题推荐与运维统计
  actions:
    - theme: brand
      text: 快速开始
      link: /course-agent

features:
  - title: 课程智能对话
    details: 支持围绕课程内容进行多轮问答、知识库检索和上下文追踪。
  - title: 课本伴读
    details: 支持 PDF 浏览、页码跳转、选区 OCR、翻译和侧边问答。
  - title: 视频伴读
    details: 支持课程视频按章节组织、字幕读取和分段总结展示。
  - title: 习题推荐
    details: 支持按章节、知识点和题型生成练习，并记录答题结果。
  - title: 运维统计
    details: 提供用户、对话、做题和反馈数据的集中查看入口。
---

## 启动

```bash
docker compose up --build -d
```

启动后访问 `http://localhost:5173`。
