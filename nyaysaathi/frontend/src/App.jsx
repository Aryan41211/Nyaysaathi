import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import HomePage       from './pages/HomePage.jsx'
import SearchPage     from './pages/SearchPage.jsx'
import ResultsPage    from './pages/ResultsPage.jsx'
import CategoriesPage from './pages/CategoriesPage.jsx'
import CaseDetailPage from './pages/CaseDetailPage.jsx'
import SignInPage     from './pages/SignInPage.jsx'

export default function App() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <main style={{ flex: 1 }}>
        <Routes>
          <Route path="/"                  element={<HomePage />} />
          <Route path="/search"            element={<SearchPage />} />
          <Route path="/results"           element={<ResultsPage />} />
          <Route path="/categories"        element={<CategoriesPage />} />
          <Route path="/case/:subcategory" element={<CaseDetailPage />} />
          <Route path="/signin"            element={<SignInPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
