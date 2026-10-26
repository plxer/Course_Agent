import { apiGet, apiPost, apiPut, apiDelete } from './base'

/**
 * 提交用户反馈（支持匿名提交）
 * @param {Object} data - 反馈数据
 * @param {string} data.category - 反馈类别: general/bug/feature/improvement
 * @param {string} data.title - 反馈标题
 * @param {string} data.content - 反馈内容
 * @param {string} [data.contact] - 联系方式（可选）
 * @returns {Promise}
 */
export function submitFeedback(data) {
  return apiPost('/api/feedback', data, {}, false) // 不需要认证
}

/**
 * 获取当前用户的反馈列表
 * @param {Object} params - 查询参数
 * @param {number} [params.skip=0] - 跳过数量
 * @param {number} [params.limit=20] - 返回数量
 * @returns {Promise}
 */
export function getMyFeedbacks(params = {}) {
  const queryParams = new URLSearchParams()
  if (params.skip !== undefined) queryParams.append('skip', params.skip)
  if (params.limit !== undefined) queryParams.append('limit', params.limit)
  const query = queryParams.toString() ? `?${queryParams.toString()}` : ''
  return apiGet(`/api/feedback/my${query}`)
}

// ============ 管理员接口 ============

/**
 * 获取所有反馈列表（管理员权限）
 * @param {Object} params - 查询参数
 * @param {number} [params.skip=0] - 跳过数量
 * @param {number} [params.limit=20] - 返回数量
 * @param {string} [params.status] - 状态过滤: pending/processing/resolved/closed
 * @param {string} [params.category] - 类别过滤: general/bug/feature/improvement
 * @returns {Promise}
 */
export function getAllFeedbacks(params = {}) {
  const queryParams = new URLSearchParams()
  if (params.skip !== undefined) queryParams.append('skip', params.skip)
  if (params.limit !== undefined) queryParams.append('limit', params.limit)
  if (params.status) queryParams.append('status', params.status)
  if (params.category) queryParams.append('category', params.category)
  const query = queryParams.toString() ? `?${queryParams.toString()}` : ''
  return apiGet(`/api/feedback/admin${query}`)
}

/**
 * 获取反馈统计数据（管理员权限）
 * @returns {Promise}
 */
export function getFeedbackStats() {
  return apiGet('/api/feedback/admin/stats')
}

/**
 * 获取反馈详情（管理员权限）
 * @param {number} feedbackId - 反馈ID
 * @returns {Promise}
 */
export function getFeedbackDetail(feedbackId) {
  return apiGet(`/api/feedback/admin/${feedbackId}`)
}

/**
 * 更新反馈状态或回复（管理员权限）
 * @param {number} feedbackId - 反馈ID
 * @param {Object} data - 更新数据
 * @param {string} [data.status] - 状态: pending/processing/resolved/closed
 * @param {string} [data.admin_reply] - 管理员回复
 * @returns {Promise}
 */
export function updateFeedback(feedbackId, data) {
  return apiPut(`/api/feedback/admin/${feedbackId}`, data)
}

/**
 * 删除反馈（管理员权限）
 * @param {number} feedbackId - 反馈ID
 * @returns {Promise}
 */
export function deleteFeedback(feedbackId) {
  return apiDelete(`/api/feedback/admin/${feedbackId}`)
}
