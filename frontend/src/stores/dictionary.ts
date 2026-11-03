import { defineStore } from 'pinia'

import { apiGet } from '../api/http'
import type {
  DictionaryDisputeType,
  DictionaryEvidenceCategory,
  DictionaryResponse,
  DictionaryStage,
} from '../types/api'

export const useDictionaryStore = defineStore('dictionary', {
  state: () => ({
    disputes: [] as DictionaryDisputeType[],
    stages: [] as DictionaryStage[],
    evidenceCategories: [] as DictionaryEvidenceCategory[],
    loaded: false,
  }),
  getters: {
    disputeLabels(state): Record<string, string> {
      return Object.fromEntries(state.disputes.map((item) => [item.value, item.label]))
    },
    laborDisputes(state): DictionaryDisputeType[] {
      return state.disputes.filter((item) => item.group === 'labor')
    },
    serviceDisputes(state): DictionaryDisputeType[] {
      return state.disputes.filter((item) => item.group === 'service')
    },
    stageLabels(state): Record<string, string> {
      return Object.fromEntries(state.stages.map((item) => [item.value, item.label]))
    },
    categoryLabels(state): Record<string, string> {
      return Object.fromEntries(
        state.evidenceCategories.map((item) => [item.value, item.label]),
      )
    },
  },
  actions: {
    async load() {
      if (this.loaded) return
      const data = await apiGet<DictionaryResponse>('/meta/dictionary')
      this.disputes = data.disputes
      this.stages = data.stages
      this.evidenceCategories = data.evidence_categories
      this.loaded = true
    },
  },
})
