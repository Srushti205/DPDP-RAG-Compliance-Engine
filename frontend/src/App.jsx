import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center gap-8 p-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-white mb-2">
          DPDP Hotel Compliance
        </h1>
        <p className="text-gray-400 text-lg">
          RAG-powered compliance analysis platform
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-indigo-400">Backend</span>
          <span className="text-2xl font-bold text-white">FastAPI</span>
          <span className="text-gray-500 text-sm">Python · RAG pipeline</span>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-violet-400">Frontend</span>
          <span className="text-2xl font-bold text-white">React + Vite</span>
          <span className="text-gray-500 text-sm">Tailwind CSS v3</span>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-emerald-400">Vector DB</span>
          <span className="text-2xl font-bold text-white">ChromaDB</span>
          <span className="text-gray-500 text-sm">BM25 + Semantic</span>
        </div>
      </div>

      {/* Counter to verify interactivity */}
      <div className="flex flex-col items-center gap-3">
        <button
          type="button"
          onClick={() => setCount((c) => c + 1)}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 transition-colors rounded-lg font-semibold text-white shadow-lg shadow-indigo-900/40"
        >
          Clicked {count} {count === 1 ? 'time' : 'times'}
        </button>
        <p className="text-gray-600 text-sm">Edit <code className="bg-gray-800 text-indigo-300 px-1.5 py-0.5 rounded text-xs">src/App.jsx</code> to get started</p>
      </div>

      {/* Tailwind working indicator */}
      <div className="flex items-center gap-2 text-sm text-emerald-400">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse inline-block"></span>
        Tailwind CSS is working correctly
      </div>
    </div>
  )
}

export default App
