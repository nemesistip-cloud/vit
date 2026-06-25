import React, { useRef } from 'react';
import './CategoryPills.css';

interface CategoryItem {
  id: string;
  label: string;
  count?: number;
}

interface CategoryPillsProps {
  items: CategoryItem[];
  activeId: string;
  onSelect: (id: string) => void;
}

export default function CategoryPills({ items, activeId, onSelect }: CategoryPillsProps) {
  const scrollRef = useRef<HTMLElement>(null);

  return (
    <nav
      className="category-pills"
      ref={scrollRef}
      role="tablist"
      aria-label="Content categories"
    >
      {items.map(({ id, label, count }) => (
        <button
          key={id}
          role="tab"
          aria-selected={activeId === id}
          className={`category-pills__item ${activeId === id ? 'category-pills__item--active' : ''}`}
          onClick={() => onSelect(id)}
        >
          {label}
          {count != null && (
            <span className="category-pills__count" aria-label={`${count} items`}>
              {count}
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}
