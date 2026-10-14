
import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { getHealth, getStores, getCategories } from '@beverage/api'
import { colors } from '@beverage/ui-tokens'
import './style.css'

function App() {
  const [health, setHealth] = useState('Checking...')
  const [stores, setStores] = useState([])
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadMarketplace() {
      try {
        const healthData = await getHealth()
        setHealth(healthData.status || 'Connected')
      } catch (err) {
        console.error('Health API failed:', err)
        setHealth('Connection failed')
        setError(`Health API failed: ${err.message}`)
        return
      }

      const [storeResult, categoryResult] = await Promise.allSettled([
        getStores(),
        getCategories(),
      ])

      if (storeResult.status === 'fulfilled') {
        const data = storeResult.value
        setStores(data.results || data)
      } else {
        console.error('Stores API failed:', storeResult.reason)
      }

      if (categoryResult.status === 'fulfilled') {
        const data = categoryResult.value
        setCategories(data.results || data)
      } else {
        console.error('Categories API failed:', categoryResult.reason)
      }

      const failures = []

      if (storeResult.status === 'rejected') {
        failures.push('stores')
      }

      if (categoryResult.status === 'rejected') {
        failures.push('categories')
      }

      setError(
        failures.length
          ? `Could not load: ${failures.join(' and ')}. Check the browser console.`
          : ''
      )
    }

    loadMarketplace()
  }, [])

  return (
    <main className="container" style={{ '--brand': colors.primary }}>
      <header className="hero">
        <p className="eyebrow">BEVERAGE DELIVERY</p>
        <h1>Find your favourite drinks</h1>
        <p>Explore stores and beverages available through our marketplace.</p>
        <span className="connection">API: {health}</span>
      </header>

      {error && <p className="error">{error}</p>}

      <section>
        <h2>Categories</h2>
        {categories.length > 0 ? (
          <div className="items">
            {categories.map((category, index) => (
              <article className="item" key={category.id ?? index}>
                {category.name || category.title || 'Beverage category'}
              </article>
            ))}
          </div>
        ) : (
          !error && <p>No categories available yet.</p>
        )}
      </section>

      <section>
        <h2>Available stores</h2>
        {stores.length > 0 ? (
          <div className="items">
            {stores.map((store, index) => (
              <article className="item" key={store.id ?? index}>
                <h3>{store.name || store.store_name || 'Beverage store'}</h3>
                <p>{store.description || store.address || 'Store details'}</p>
              </article>
            ))}
          </div>
        ) : (
          !error && <p>No stores available yet.</p>
        )}
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
