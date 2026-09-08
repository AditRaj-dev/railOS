import type { ReactNode, TableHTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react';

interface TableProps extends TableHTMLAttributes<HTMLTableElement> {
  caption: string;
  children: ReactNode;
}

/** Semantic table wrapper with an always-present accessible caption. */
export function Table({ caption, children, className = '', ...props }: TableProps) {
  return (
    <div className="overflow-x-auto rounded border border-[var(--border-default)]">
      <table
        {...props}
        className={`w-full border-collapse text-left text-sm ${className}`}
      >
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ children }: { children: ReactNode }) {
  return (
    <thead className="bg-[var(--bg-elevated)] text-xs font-mono uppercase tracking-wide text-[var(--text-secondary)]">
      {children}
    </thead>
  );
}

export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-[var(--border-subtle)]">{children}</tbody>;
}

export function TableCell({ children, className = '', ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td {...props} className={`px-3 py-3 align-top ${className}`}>
      {children}
    </td>
  );
}

export function TableHeaderCell({ children, className = '', ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th {...props} scope="col" className={`px-3 py-3 text-left font-semibold ${className}`}>
      {children}
    </th>
  );
}
