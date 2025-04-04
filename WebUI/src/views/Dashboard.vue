<template>
  <div class="dashboard">
    <div class="dashboard-container">
      <div class="stats-grid">
        <n-card
          v-for="stat in stats"
          :key="stat.title"
          :title="stat.title"
          class="stat-card"
          size="small"
          :bordered="false"
        >
          <div class="stat-content">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-icon">
              <n-icon :color="stat.color" :size="24">
                <component :is="stat.icon" />
              </n-icon>
            </div>
          </div>
        </n-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { 
  PeopleOutline, 
  VideocamOutline, 
  RecordingOutline, 
  ServerOutline 
} from '@vicons/ionicons5';
import { computed } from 'vue';
import { useRoomStore } from '@/lib/store/room';
import { useServerStore } from '@/lib/store/server';
import { useRoomUtils } from '@/lib/utils/useRoomUtils';

const roomStore = useRoomStore();
const serverStore = useServerStore();
const { isStreaming, isRecording } = useRoomUtils();
const streamingRooms = computed(() => 
  roomStore.rooms.filter(room => isStreaming(room))
);
const recordingRooms = computed(() => 
  roomStore.rooms.filter(room => isRecording(room))
);
const onlineServers = computed(() => 
  serverStore.servers.filter(server => server.recStatus === 'online')
);

const stats = computed(() => [
  {
    title: '监控房间',
    value: roomStore.rooms.length || 0,
    icon: PeopleOutline,
    color: '#2080f0'
  },
  {
    title: '直播中',
    value: streamingRooms.value.length || 0,
    icon: VideocamOutline,
    color: '#d03050'
  },
  {
    title: '录制中',
    value: recordingRooms.value.length || 0,
    icon: RecordingOutline,
    color: '#18a058'
  },
  {
    title: '录播机',
    value: onlineServers.value.length || 0,
    icon: ServerOutline,
    color: '#2080f0'
  }
]);
</script>

<style scoped lang="scss">
.dashboard {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;

  .dashboard-container {
    width: 100%;
    max-width: 1200px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin: 0 auto;

    .stat-card {
      border-radius: 12px;
      transition: all 0.3s ease;
      background-color: var(--n-card-color);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
      }

      :deep(.n-card-header) {
        padding: 16px 20px;
        font-size: 15px;
      }

      :deep(.n-card__content) {
        padding: 0 20px 16px;
      }

      .stat-content {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .stat-value {
          font-size: 24px;
          font-weight: 600;
          color: var(--n-text-color);
        }

        .stat-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background-color: var(--n-card-color);
        }
      }
    }
  }
}

html.dark {
  .dashboard {
    .stats-grid {
      .stat-card {
        background-color: var(--n-card-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);

        &:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
      }
    }
  }
}
</style> 