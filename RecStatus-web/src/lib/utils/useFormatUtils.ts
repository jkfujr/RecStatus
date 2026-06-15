/**
 * 格式化时长
 * @param seconds 秒数
 * @returns 格式化后的时长字符串
 */
export function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0秒'
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = Math.floor(seconds % 60)

  const parts = []
  if (hours > 0) parts.push(`${hours}小时`)
  if (minutes > 0) parts.push(`${minutes}分钟`)
  if (remainingSeconds > 0) parts.push(`${remainingSeconds}秒`)

  return parts.join('')
}

/**
 * 格式化速率
 * @param bytesPerSecond 每秒字节数
 * @returns 格式化后的速率字符串
 */
export function formatDataRate(bytesPerSecond: number): string {
  if (!bytesPerSecond || bytesPerSecond <= 0) return '0 B/s'
  
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  let value = bytesPerSecond
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex++
  }

  return `${value.toFixed(2)} ${units[unitIndex]}`
} 