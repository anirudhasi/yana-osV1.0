// src/components/tables/RidersTable.jsx
import { useState, useMemo } from 'react'
import {
  useReactTable, getCoreRowModel, getFilteredRowModel,
  getSortedRowModel, getPaginationRowModel, flexRender,
  createColumnHelper,
} from '@tanstack/react-table'
import { clsx } from 'clsx'
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { Badge, Avatar } from '../ui'
import { format } from 'date-fns'

const col = createColumnHelper()

const columns = [
  col.display({
    id: 'rider',
    header: 'Rider',
    cell: ({ row }) => {
      const r = row.original
      return (
        <div className="flex items-center gap-3">
          <Avatar name={r.full_name} />
          <div>
            <p className="font-medium text-surface-900 text-sm leading-tight">{r.full_name}</p>
            <p className="text-xs text-surface-400 font-mono">{r.phone}</p>
          </div>
        </div>
      )
    },
  }),
  col.accessor('status', {
    header: 'Status',
    cell: (info) => <Badge status={info.getValue()} label={info.getValue().replace('_', ' ')} />,
    filterFn: 'equals',
  }),
  col.accessor('kyc_status', {
    header: 'KYC',
    cell: (info) => <Badge status={info.getValue()} label={info.getValue().replace('_', ' ')} />,
  }),
  col.accessor('city', {
    header: 'City',
    cell: (info) => <span className="text-sm text-surface-600">{info.getValue()}</span>,
  }),
  col.accessor('hub', {
    header: 'Hub',
    cell: (info) => <span className="text-xs text-surface-500 max-w-[120px] truncate block">{info.getValue()}</span>,
  }),
  col.accessor('wallet_balance', {
    header: 'Wallet',
    cell: (info) => {
      const v = info.getValue()
      return (
        <span className={clsx('text-sm font-mono font-medium', v < 100 ? 'text-red-500' : 'text-surface-700')}>
          {v ? `₹${v.toLocaleString()}` : '—'}
        </span>
      )
    },
  }),
  col.accessor('reliability_score', {
    header: 'Score',
    cell: (info) => {
      const v = info.getValue()
      if (!v) return <span className="text-surface-300">—</span>
      const color = v >= 8 ? 'text-brand-600' : v >= 6 ? 'text-amber-600' : 'text-red-500'
      return <span className={clsx('text-sm font-mono font-bold', color)}>{v}</span>
    },
  }),
  col.accessor('created_at', {
    header: 'Joined',
    cell: (info) => (
      <span className="text-xs text-surface-400">
        {format(new Date(info.getValue()), 'dd MMM yy')}
      </span>
    ),
  }),
]

const STATUS_FILTERS = ['ALL','ACTIVE','KYC_PENDING','VERIFIED','TRAINING','SUSPENDED']

export default function RidersTable({ data }) {
  const [globalFilter, setGlobalFilter]   = useState('')
  const [statusFilter, setStatusFilter]   = useState('ALL')
  const [sorting, setSorting]             = useState([])

  const filtered = useMemo(() =>
    statusFilter === 'ALL' ? data : data.filter(r => r.status === statusFilter),
    [data, statusFilter]
  )

  const table = useReactTable({
    data: filtered,
    columns,
    state:          { sorting, globalFilter },
    onSortingChange:       setSorting,
    onGlobalFilterChange:  setGlobalFilter,
    getCoreRowModel:       getCoreRowModel(),
    getFilteredRowModel:   getFilteredRowModel(),
    getSortedRowModel:     getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState:          { pagination: { pageSize: 10 } },
  })

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
          <input
            className="input pl-9 h-9 w-56"
            placeholder="Search name or phone…"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1">
          {STATUS_FILTERS.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={clsx('px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                statusFilter === s
                  ? 'bg-brand-600 text-white'
                  : 'bg-surface-100 text-surface-500 hover:bg-surface-200'
              )}>
              {s === 'ALL' ? 'All' : s.replace('_', ' ')}
            </button>
          ))}
        </div>
        <span className="ml-auto text-xs text-surface-400">{filtered.length} riders</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-surface-200">
        <table className="w-full text-left">
          <thead>
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id} className="border-b border-surface-100 bg-surface-50">
                {hg.headers.map(header => (
                  <th key={header.id}
                    className="px-4 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider whitespace-nowrap cursor-pointer select-none"
                    onClick={header.column.getToggleSortingHandler()}>
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        header.column.getIsSorted() === 'asc'  ? <ChevronUp size={12} className="text-brand-500" /> :
                        header.column.getIsSorted() === 'desc' ? <ChevronDown size={12} className="text-brand-500" /> :
                        <ChevronsUpDown size={12} className="text-surface-300" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, i) => (
              <tr key={row.id}
                className={clsx('border-b border-surface-50 hover:bg-surface-50/80 transition-colors',
                  i % 2 === 0 ? 'bg-white' : 'bg-surface-50/30'
                )}>
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-4 py-3 whitespace-nowrap">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-surface-400">
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
        </p>
        <div className="flex items-center gap-1">
          <button onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}
            className="btn-ghost py-1.5 px-2 text-xs disabled:opacity-30">
            <ChevronLeft size={14} />
          </button>
          {Array.from({ length: Math.min(table.getPageCount(), 5) }, (_, i) => (
            <button key={i}
              onClick={() => table.setPageIndex(i)}
              className={clsx('w-7 h-7 rounded-lg text-xs font-medium transition-all',
                table.getState().pagination.pageIndex === i
                  ? 'bg-brand-600 text-white'
                  : 'hover:bg-surface-100 text-surface-500'
              )}>
              {i + 1}
            </button>
          ))}
          <button onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}
            className="btn-ghost py-1.5 px-2 text-xs disabled:opacity-30">
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
