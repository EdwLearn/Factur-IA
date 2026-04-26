export default function Loading() {
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3 text-gray-500">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
        <span className="text-sm">Cargando factura...</span>
      </div>

      {/* Header skeleton */}
      <div className="rounded-lg border bg-white p-6 space-y-3 animate-pulse">
        <div className="h-7 w-48 bg-gray-200 rounded" />
        <div className="h-5 w-64 bg-gray-100 rounded" />
        <div className="h-4 w-32 bg-gray-100 rounded" />
      </div>

      {/* Table skeleton */}
      <div className="rounded-lg border bg-white p-6 space-y-3 animate-pulse">
        <div className="h-6 w-40 bg-gray-200 rounded" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 w-full bg-gray-100 rounded" />
        ))}
      </div>

      {/* Totals skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-lg border bg-white p-6 space-y-3 animate-pulse">
          <div className="h-6 w-32 bg-gray-200 rounded" />
          <div className="h-5 w-full bg-gray-100 rounded" />
          <div className="h-5 w-full bg-gray-100 rounded" />
          <div className="h-6 w-40 bg-gray-200 rounded" />
        </div>
        <div className="rounded-lg border bg-white p-6 animate-pulse">
          <div className="h-6 w-40 bg-gray-200 rounded mb-4" />
          <div className="h-20 w-full bg-gray-100 rounded" />
        </div>
      </div>
    </div>
  )
}
