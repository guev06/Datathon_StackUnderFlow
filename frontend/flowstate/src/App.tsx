import { Route, Routes } from 'react-router-dom';
import Landing from './pages/Landing';
import Explorer from './pages/Explorer';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/explore" element={<Explorer />} />
    </Routes>
  );
}
