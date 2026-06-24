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
