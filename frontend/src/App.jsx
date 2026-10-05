import { useEffect, useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [donations, setDonations] = useState([])
  const [totalAmount, setTotalAmount] = useState(0)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const loadDonations = async () => {
    try {
      const res = await fetch(`${API_URL}/donations`)
      if (!res.ok) throw new Error('Failed to load donations')
      const data = await res.json()
      setDonations(data.donations)
      setTotalAmount(data.total_amount)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDonations()
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    const parsedAmount = parseFloat(amount)
    if (!name.trim() || !(parsedAmount > 0)) {
      setError('Enter a name and an amount greater than zero.')
      return
    }

    try {
      const res = await fetch(`${API_URL}/donations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, amount: parsedAmount }),
      })
      if (!res.ok) throw new Error('Failed to log donation')

      setName('')
      setAmount('')
      await loadDonations()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="page">
      <h1>Donation Tracker</h1>

      <section className="total-card">
        <span className="total-label">Total raised</span>
        <span className="total-amount">${totalAmount.toFixed(2)}</span>
        <span className="total-count">{donations.length} donation{donations.length === 1 ? '' : 's'}</span>
      </section>

      <form className="donation-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Your name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <input
          type="number"
          step="0.01"
          min="0.01"
          placeholder="Amount"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
        <button type="submit">Donate</button>
      </form>

      {error && <p className="error">{error}</p>}

      <section className="donation-list">
        <h2>Recent donations</h2>
        {loading ? (
          <p>Loading...</p>
        ) : donations.length === 0 ? (
          <p>No donations yet. Be the first!</p>
        ) : (
          <ul>
            {[...donations].reverse().map((donation) => (
              <li key={donation.id}>
                <span>{donation.name}</span>
                <span>${donation.amount.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}

export default App
