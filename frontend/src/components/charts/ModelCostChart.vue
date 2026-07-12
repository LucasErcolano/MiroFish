<template>
  <div class="model-chart">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend)

const props = defineProps({
  rows: {
    type: Array,
    default: () => []
  }
})

const chartData = computed(() => ({
  labels: props.rows.map(row => row.model),
  datasets: [
    {
      label: 'Estimated cost',
      data: props.rows.map(row => Number(row.cost_usd_est || 0)),
      backgroundColor: '#111827'
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  scales: {
    y: { beginAtZero: true }
  }
}
</script>

<style scoped>
.model-chart {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.model-chart :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
}
</style>
