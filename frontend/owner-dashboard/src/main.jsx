import React from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

function App() {
  return (
    <main className="dashboard">
      <header>
        <h1>Owner Dashboard</h1>
        <p>Manage your beverage store in one place.</p>
      </header>

      <section className="cards">
        <article className="card">
          <h2>Orders</h2>
          <p>View and manage customer orders.</p>
        </article>

        <article className="card">
          <h2>Products</h2>
          <p>Manage beverages, prices, and stock.</p>
        </article>

        <article className="card">
          <h2>Store</h2>
          <p>Manage your store information.</p>
        </article>
      </section>

      <p className="status">Owner dashboard is running.</p>
    </main>
  )
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
