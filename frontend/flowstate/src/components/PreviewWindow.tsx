import { CSSProperties, ReactNode } from 'react';
import './PreviewWindow.css';

type Props = {
  title: string;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
};

export default function PreviewWindow({ title, children, className = '', style }: Props) {
  return (
    <div className={`pw ${className}`} style={style}>
      <div className="pw-bar">
        <span className="pw-dot" />
        <span className="pw-dot" />
        <span className="pw-dot" />
        <span className="pw-title mono">{title}</span>
      </div>
      <div className="pw-body">{children}</div>
    </div>
  );
}
