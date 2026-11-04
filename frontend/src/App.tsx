import { Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import TextToSpeech from './pages/TextToSpeech'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<TextToSpeech />} />
      </Route>
    </Routes>
  )
}
