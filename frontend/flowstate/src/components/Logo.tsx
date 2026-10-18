import { Link } from 'react-router-dom';
import { brand } from '../config/brand';

export default function Logo() {
  return (
    <Link to="/" className="logo">
      <img src={brand.logo} alt="" width={24} height={24} />
      <span>{brand.name}</span>
    </Link>
  );
}
