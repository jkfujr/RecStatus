interface VirtualListOptions {
  itemHeight: number
  bufferSize?: number
  pageSize?: number
}

interface VirtualListReturn<T> {
  containerRef: any
  visibleItems: ComputedRef<T[]>
  totalHeight: ComputedRef<number>
  offsetY: ComputedRef<number>
}

export function useVirtualList<T>(
  items: ComputedRef<T[]>,
  options: VirtualListOptions
): VirtualListReturn<T> {
  const containerRef = ref<HTMLElement | null>(null)
  const scrollTop = ref(0)
  const bufferSize = options.bufferSize || 5

  onMounted(() => {
    const container = containerRef.value
    if (container) {
      container.addEventListener('scroll', handleScroll)
    }
  })

  onUnmounted(() => {
    const container = containerRef.value
    if (container) {
      container.removeEventListener('scroll', handleScroll)
    }
  })

  const handleScroll = (e: Event) => {
    const target = e.target as HTMLElement
    scrollTop.value = target.scrollTop
  }

  const visibleItems = computed(() => {
    const start = Math.floor(scrollTop.value / options.itemHeight)
    const visibleCount = Math.ceil(window.innerHeight / options.itemHeight)
    const startIndex = Math.max(0, start - bufferSize)
    const endIndex = Math.min(items.value.length, start + visibleCount + bufferSize)
    return items.value.slice(startIndex, endIndex)
  })

  const totalHeight = computed(() => items.value.length * options.itemHeight)

  const offsetY = computed(() => {
    const start = Math.floor(scrollTop.value / options.itemHeight)
    const startIndex = Math.max(0, start - bufferSize)
    return startIndex * options.itemHeight
  })

  return {
    containerRef,
    visibleItems,
    totalHeight,
    offsetY
  }
} 