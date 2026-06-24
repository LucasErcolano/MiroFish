<template>
  <Bar :data="chartData" :options="chartOptions" />
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
      label: 'p50 latency',
      data: props.rows.map(row => Number(row.latency_p50_ms || 0)),
      backgroundColor: '#2563EB'
    },
    {
      label: 'p95 latency',
      data: props.rows.map(row => Number(row.latency_p95_ms || 0)),
      backgroundColor: '#F97316'
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' }
  },
  scales: {
    y: { beginAtZero: true }
  }
}
</script>
