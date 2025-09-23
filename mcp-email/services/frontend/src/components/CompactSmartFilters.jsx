import React, { useState } from 'react';
import { ChevronDown, Plus, X } from 'lucide-react';

const CompactSmartFilters = ({ activeFilters, onFilterChange }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Predefinerade filter
  const availableFilters = [
    { id: 'news', label: 'Nyheter', icon: '📰' },
    { id: 'work', label: 'Arbete', icon: '💼' },
    { id: 'important', label: 'Viktigt', icon: '⭐' },
    { id: 'unread', label: 'Oläst', icon: '🔵' },
    { id: 'invoices', label: 'Fakturor', icon: '📊' },
    { id: 'offers', label: 'Erbjudanden', icon: '🛍️' },
    { id: 'meetings', label: 'Möten', icon: '🗓️' },
    { id: 'personal', label: 'Personligt', icon: '👤' },
    { id: 'spam', label: 'Spam', icon: '🗑️' },
    { id: 'deliveries', label: 'Leverans', icon: '📦' }
  ];

  const [selectedFilters, setSelectedFilters] = useState(['news']);

  const handleFilterSelect = (filterId) => {
    setSelectedFilters(prev => {
      if (prev.includes(filterId)) {
        return prev.filter(id => id !== filterId);
      }
      return [...prev, filterId];
    });
    onFilterChange?.(filterId);
  };

  const handleQuickAdd = (filterId) => {
    if (!selectedFilters.includes(filterId)) {
      handleFilterSelect(filterId);
    }
  };

  const clearAllFilters = () => {
    setSelectedFilters([]);
    onFilterChange?.('clear_all');
  };

  const mainFilter = availableFilters.find(f => f.id === selectedFilters[0]);
  const quickFilters = ['work', 'important', 'unread'];

  return (
    <div className="compact-smart-filters">
      <div className="filter-row-1">
        {/* Huvudfilter dropdown */}
        <div className="main-filter-dropdown">
          <button
            className="dropdown-trigger"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            <ChevronDown size={16} />
            <span>Smarta filter: </span>
            {mainFilter ? (
              <>
                <span className="filter-icon">{mainFilter.icon}</span>
                <span className="filter-label">{mainFilter.label}</span>
              </>
            ) : (
              <span className="filter-label">Välj filter</span>
            )}
          </button>

          {isDropdownOpen && (
            <div className="dropdown-menu">
              {availableFilters.map(filter => (
                <div
                  key={filter.id}
                  className={`dropdown-item ${selectedFilters.includes(filter.id) ? 'active' : ''}`}
                  onClick={() => {
                    handleFilterSelect(filter.id);
                    setIsDropdownOpen(false);
                  }}
                >
                  <span className="filter-icon">{filter.icon}</span>
                  <span>{filter.label}</span>
                  {selectedFilters.includes(filter.id) && (
                    <span className="checkmark">✓</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Snabbval knappar */}
        {quickFilters.map(filterId => {
          const filter = availableFilters.find(f => f.id === filterId);
          const isActive = selectedFilters.includes(filterId);

          return (
            <button
              key={filterId}
              className={`quick-filter-btn ${isActive ? 'active' : ''}`}
              onClick={() => handleQuickAdd(filterId)}
            >
              <Plus size={14} />
              <span>{filter.label}</span>
            </button>
          );
        })}

        {/* Oläst räknare */}
        <div className="unread-counter">
          <span className="badge">23</span>
        </div>
      </div>

      <div className="filter-row-2">
        {/* Anpassa filter */}
        <button className="customize-btn">
          Anpassa filter...
        </button>

        {/* Rensa alla */}
        <button
          className="clear-all-btn"
          onClick={clearAllFilters}
          disabled={selectedFilters.length === 0}
        >
          Rensa alla
        </button>

        {/* Aktiva filter chips */}
        <div className="active-filters">
          {selectedFilters.map(filterId => {
            const filter = availableFilters.find(f => f.id === filterId);
            return (
              <div key={filterId} className="filter-chip">
                <span>{filter.icon}</span>
                <span>{filter.label}</span>
                <button
                  className="remove-btn"
                  onClick={() => handleFilterSelect(filterId)}
                >
                  <X size={12} />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <style jsx>{`
        .compact-smart-filters {
          background: #ffffff;
          border-bottom: 1px solid #e5e7eb;
          padding: 8px 16px;
        }

        .filter-row-1, .filter-row-2 {
          display: flex;
          align-items: center;
          gap: 12px;
          height: 32px;
        }

        .filter-row-2 {
          margin-top: 4px;
        }

        /* Huvudfilter dropdown */
        .main-filter-dropdown {
          position: relative;
        }

        .dropdown-trigger {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .dropdown-trigger:hover {
          background: #e5e7eb;
          border-color: #9ca3af;
        }

        .filter-icon {
          font-size: 16px;
        }

        .filter-label {
          font-weight: 500;
        }

        .dropdown-menu {
          position: absolute;
          top: calc(100% + 4px);
          left: 0;
          min-width: 200px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          z-index: 1000;
          max-height: 300px;
          overflow-y: auto;
        }

        .dropdown-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          cursor: pointer;
          font-size: 14px;
          transition: background 0.2s;
        }

        .dropdown-item:hover {
          background: #f3f4f6;
        }

        .dropdown-item.active {
          background: #eff6ff;
          color: #2563eb;
        }

        .checkmark {
          margin-left: auto;
          color: #10b981;
        }

        /* Snabbval knappar */
        .quick-filter-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 10px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .quick-filter-btn:hover {
          background: #f3f4f6;
          border-color: #9ca3af;
        }

        .quick-filter-btn.active {
          background: #2563eb;
          color: white;
          border-color: #2563eb;
        }

        /* Oläst räknare */
        .unread-counter {
          margin-left: auto;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 24px;
          height: 24px;
          padding: 0 6px;
          background: #ef4444;
          color: white;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }

        /* Anpassa och rensa knappar */
        .customize-btn, .clear-all-btn {
          padding: 6px 12px;
          background: transparent;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .customize-btn:hover, .clear-all-btn:hover:not(:disabled) {
          background: #f3f4f6;
          border-color: #9ca3af;
        }

        .clear-all-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Aktiva filter chips */
        .active-filters {
          display: flex;
          gap: 8px;
          flex: 1;
        }

        .filter-chip {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          background: #eff6ff;
          border: 1px solid #93c5fd;
          border-radius: 16px;
          font-size: 12px;
        }

        .filter-chip .remove-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          background: transparent;
          border: none;
          border-radius: 50%;
          cursor: pointer;
          transition: background 0.2s;
        }

        .filter-chip .remove-btn:hover {
          background: rgba(0, 0, 0, 0.1);
        }

        /* Responsiv design */
        @media (max-width: 768px) {
          .compact-smart-filters {
            padding: 6px 12px;
          }

          .filter-row-1, .filter-row-2 {
            gap: 8px;
          }

          .quick-filter-btn span {
            display: none;
          }

          .quick-filter-btn {
            padding: 6px;
          }
        }
      `}</style>
    </div>
  );
};

export default CompactSmartFilters;