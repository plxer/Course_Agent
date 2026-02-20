import { Database, Waypoints, DatabaseZap } from 'lucide-vue-next'

export const getKbTypeLabel = (type) => {
  const labels = {
    lightrag: 'LightRAG',
    milvus: 'CommonRAG',
    chroma: 'Chroma'
  }
  return labels[type] || type
}

export const getKbTypeIcon = (type) => {
  const icons = {
    lightrag: Waypoints,
    milvus: DatabaseZap,
    chroma: DatabaseZap
  }
  return icons[type] || Database
}

export const getKbTypeColor = (type) => {
  const colors = {
    lightrag: 'purple',
    milvus: 'red',
    chroma: 'blue'
  }
  return colors[type] || 'blue'
}
