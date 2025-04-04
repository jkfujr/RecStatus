<template>
  <div class="home">
    <div class="home-container">
      <div class="stats-overview">
        <n-card class="stat-card" hoverable>
          <template #header>
            <div class="card-header">
              <span>监控中</span>
            </div>
          </template>
          <div class="stat-value">
            <span class="number">{{ roomStore.totalUsers }}</span>
            <span class="label">个</span>
          </div>
        </n-card>
        <n-card class="stat-card streaming-card" hoverable>
          <template #header>
            <div class="card-header">
              <span>直播中</span>
            </div>
          </template>
          <div class="stat-value">
            <span class="number">{{ roomStore.streamingUsers }}</span>
            <span class="label">个</span>
          </div>
        </n-card>
        <n-card class="stat-card recording-card" hoverable>
          <template #header>
            <div class="card-header">
              <span>录制中</span>
            </div>
          </template>
          <div class="stat-value">
            <span class="number">{{ roomStore.recordingUsers }}</span>
            <span class="label">个</span>
          </div>
        </n-card>
        <n-card class="stat-card" hoverable>
          <template #header>
            <div class="card-header">
              <span>录播机</span>
            </div>
          </template>
          <div class="stat-value">
            <span class="number">{{ serverStore.servers.length }}</span>
            <span class="label">个</span>
          </div>
        </n-card>
      </div>

      <n-alert
        v-if="roomStore.error || serverStore.error"
        type="error"
        closable
        class="mb-4"
      >{{ roomStore.error || serverStore.error }}</n-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoomStore } from '@/lib/store/room'
import { useServerStore } from '@/lib/store/server'

const roomStore = useRoomStore()
const serverStore = useServerStore()

async function initData() {
  await Promise.all([
    serverStore.fetchServers(),
    roomStore.fetchRooms()
  ])
}

onMounted(() => {
  initData()
})
</script>

<style scoped lang="scss">
.home {
  min-height: 100%;
  display: flex;
  flex-direction: column;

  .home-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 24px;
    min-height: calc(100vh - 64px - 48px);
  }

  .stats-overview {
    width: 100%;
    max-width: 1200px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-bottom: 24px;

    .stat-card {
      border-radius: 12px;
      transition: all 0.3s ease;
      overflow: hidden;

      &:hover {
        transform: translateY(-2px);
      }

      &.streaming-card {
        :deep(.n-card-header),
        :deep(.n-card__content) {
          background-color: rgba(38, 155, 71, 0.15);
        }
      }

      &.recording-card {
        :deep(.n-card-header),
        :deep(.n-card__content) {
          background-color: rgba(237, 64, 64, 0.15);
        }
      }

      .card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        font-weight: 500;
      }

      .stat-value {
        display: flex;
        align-items: baseline;
        gap: 4px;
        padding: 8px 0;

        .number {
          font-size: 32px;
          font-weight: 600;
          line-height: 1;
        }

        .label {
          font-size: 14px;
          color: var(--n-text-color-2);
        }
      }
    }
  }

  @media screen and (max-width: 1400px) {
    .stats-overview {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media screen and (max-width: 768px) {
    .stats-overview {
      grid-template-columns: 1fr;
    }
  }

  .mb-4 {
    margin-bottom: 16px;
  }
}

html.dark {
  .home {
    .stat-card {
      &:hover {
        box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.2);
      }
    }

    .streaming-card {
      :deep(.n-card-header),
      :deep(.n-card__content) {
        background-color: rgba(38, 155, 71, 0.25);
      }
    }

    .recording-card {
      :deep(.n-card-header),
      :deep(.n-card__content) {
        background-color: rgba(237, 64, 64, 0.25);
      }
    }
  }
}

:deep(.n-card.streaming-card) {
  html.dark & {
    .n-card-header,
    .n-card__content {
      background-color: rgba(38, 155, 71, 0.25);
    }
  }
}

:deep(.n-card.recording-card) {
  html.dark & {
    .n-card-header,
    .n-card__content {
      background-color: rgba(237, 64, 64, 0.25);
    }
  }
}
</style> 