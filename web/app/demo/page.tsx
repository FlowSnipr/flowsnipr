'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { createChart, IChartApi } from 'lightweight-charts'

// AG Grid v34+ requires module registration
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
ModuleRegistry.registerModules([AllCommunityModule])
import { AgGridReact } from 'ag-grid-react'

type Row = { symbol: string; price: number; changePct: number }

export default function DemoPage() {
  // ---- Chart ----
  const chartRef = useRef<HTMLDivElement | null>(null)
  const chartApi = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartRef.current) return

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 320,
      layout: {
        textColor: 'white',
        background: { type: 'solid', color: '#0a0a0a' }, // v4 style
      },
      grid: { vertLines: { color: '#222' }, horzLines: { color: '#222' } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    })
    chartApi.current = chart

    const series = chart.addAreaSeries({ lineWidth: 2, priceLineVisible: false })

    const now = Math.floor(Date.now() / 1000)
    const data = Array.from({ length: 60 }, (_, i) => ({
      time: (now - (60 - i) * 60) as any, // last 60 minutes
      value: 100 + Math.sin(i / 6) * 3 + Math.random() * 1.2,
    }))
    series.setData(data)

    const ro = new ResizeObserver(([e]) =>
      chart.applyOptions({ width: e.contentRect.width })
    )
    ro.observe(chartRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [])

  // ---- Grid ----
  const columnDefs = useMemo(
    () => [
      { field: 'symbol', headerName: 'Symbol', sortable: true, filter: true },
      { field: 'price', headerName: 'Price', sortable: true, valueFormatter: (p: any) => p.value.toFixed(2) },
      {
        field: 'changePct',
        headerName: 'Δ%',
        sortable: true,
        valueFormatter: (p: any) => `${p.value.toFixed(2)}%`,
        cellClassRules: {
          'text-green-400': (p: any) => p.value >= 0,
          'text-red-400': (p: any) => p.value < 0,
        },
      },
    ],
    []
  )

  const [rowData] = useState<Row[]>([
    { symbol: 'AAPL', price: 224.12, changePct: 0.86 },
    { symbol: 'MSFT', price: 418.02, changePct: -0.34 },
    { symbol: 'NVDA', price: 118.77, changePct: 1.42 },
  ])

  return (
    <main className="mx-auto max-w-6xl p-6 space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Demo: Chart + Grid</h1>

      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4 shadow">
        <div ref={chartRef} className="w-full" style={{ height: 320 }} />
      </div>

      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4 shadow">
        {/* Using legacy theme to avoid Theming API conflict for now */}
        <div className="ag-theme-quartz" style={{ height: 320, width: '100%' }}>
          <AgGridReact
            rowData={rowData}
            columnDefs={columnDefs as any}
            theme="legacy"
          />
        </div>
      </div>
    </main>
  )
}
