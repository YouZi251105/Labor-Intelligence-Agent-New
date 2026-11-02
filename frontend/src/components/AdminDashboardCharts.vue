<template>
  <section class="dashboard-chart-grid">
    <article class="detail-card dashboard-chart-card dashboard-chart-card--wide">
      <div class="dashboard-card-heading">
        <div>
          <span class="eyebrow">近 7 天趋势</span>
          <h2>新增用户与案件</h2>
        </div>
        <span class="status-tag">实时汇总</span>
      </div>
      <VChart class="dashboard-chart" :option="trendOption" autoresize />
    </article>

    <article class="detail-card dashboard-chart-card">
      <div class="dashboard-card-heading">
        <div>
          <span class="eyebrow">纠纷构成</span>
          <h2>问题类型分布</h2>
        </div>
      </div>
      <VChart class="dashboard-chart" :option="disputeOption" autoresize />
    </article>

    <article class="detail-card dashboard-chart-card">
      <div class="dashboard-card-heading">
        <div>
          <span class="eyebrow">办理进度</span>
          <h2>案件阶段分布</h2>
        </div>
      </div>
      <VChart class="dashboard-chart" :option="stageOption" autoresize />
    </article>
  </section>
</template>

<script setup lang="ts">
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'
import VChart from 'vue-echarts'

import type { AdminDashboardData } from '../types/api'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
])

const props = defineProps<{
  data: AdminDashboardData
}>()

const colors = ['#a61b1b', '#31465f', '#2f7d5a', '#a66a16', '#7b8490']

const trendOption = computed<EChartsOption>(() => ({
  color: colors,
  tooltip: { trigger: 'axis' },
  legend: {
    right: 8,
    top: 0,
    textStyle: { color: '#5b6472', fontSize: 12 },
  },
  grid: { left: 36, right: 18, top: 42, bottom: 26 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: props.data.trends.map((item) => item.date.slice(5)),
    axisLine: { lineStyle: { color: '#d8d1c7' } },
    axisLabel: { color: '#7b8490' },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#eee9e3' } },
    axisLabel: { color: '#7b8490' },
  },
  series: [
    {
      name: '新增用户',
      type: 'line',
      smooth: true,
      symbolSize: 7,
      data: props.data.trends.map((item) => item.users),
      areaStyle: { opacity: 0.08 },
    },
    {
      name: '新增案件',
      type: 'line',
      smooth: true,
      symbolSize: 7,
      data: props.data.trends.map((item) => item.cases),
      areaStyle: { opacity: 0.06 },
    },
  ],
}))

const disputeOption = computed<EChartsOption>(() => ({
  color: colors,
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 件（{d}%）' },
  legend: {
    bottom: 0,
    type: 'scroll',
    textStyle: { color: '#5b6472', fontSize: 11 },
  },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderColor: '#fff', borderWidth: 3 },
      label: { show: false },
      data: props.data.disputes.map((item) => ({
        name: item.label,
        value: item.count,
      })),
    },
  ],
}))

const stageOption = computed<EChartsOption>(() => ({
  color: colors,
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 86, right: 20, top: 18, bottom: 28 },
  xAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#eee9e3' } },
    axisLabel: { color: '#7b8490' },
  },
  yAxis: {
    type: 'category',
    data: props.data.stages.map((item) => item.label),
    axisLabel: { color: '#5b6472' },
    axisLine: { lineStyle: { color: '#d8d1c7' } },
  },
  series: [
    {
      type: 'bar',
      data: props.data.stages.map((item) => item.count),
      barWidth: 14,
      itemStyle: { borderRadius: [0, 4, 4, 0] },
    },
  ],
}))
</script>
