/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import ScoreBadge from '@/components/ScoreBadge';

describe('ScoreBadge', () => {
  it('should render score value', () => {
    render(<ScoreBadge score={75} />);
    expect(screen.getByText('75')).toBeInTheDocument();
  });

  it('should apply correct styling for hot articles', () => {
    render(<ScoreBadge score={85} />);
    const badge = screen.getByText('85').parentElement;
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('should apply correct styling for interesting articles', () => {
    render(<ScoreBadge score={65} />);
    const badge = screen.getByText('65').parentElement;
    expect(badge).toHaveClass('bg-amber-100', 'text-amber-800');
  });

  it('should apply default styling for low score articles', () => {
    render(<ScoreBadge score={30} />);
    const badge = screen.getByText('30').parentElement;
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
  });

  it('should show emoji for hot articles', () => {
    render(<ScoreBadge score={85} />);
    expect(screen.getByText('🔥')).toBeInTheDocument();
  });

  it('should show emoji for interesting articles', () => {
    render(<ScoreBadge score={65} />);
    expect(screen.getByText('✨')).toBeInTheDocument();
  });

  it('should not show emoji for low score articles', () => {
    render(<ScoreBadge score={30} />);
    expect(screen.queryByText('🔥')).not.toBeInTheDocument();
    expect(screen.queryByText('✨')).not.toBeInTheDocument();
  });

  it('should show tooltip with breakdown when provided', () => {
    const breakdown = {
      keywords: 10,
      watchlist: 5,
      source: 3,
      image_bonus: 3,
      recency_factor: 0.9,
      base_score: 21
    };

    render(<ScoreBadge score={75} breakdown={breakdown} />);
    
    const badge = screen.getByText('75').parentElement;
    fireEvent.mouseEnter(badge!);
    
    // Check tooltip content
    expect(screen.getByText('Score Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Keywords: 10')).toBeInTheDocument();
    expect(screen.getByText('Image: +3')).toBeInTheDocument();
    expect(screen.getByText('Base: 21 → Final: 75')).toBeInTheDocument();
  });

  it('should use custom thresholds', () => {
    const customThreshold = { star: 90, interesting: 70 };
    
    render(<ScoreBadge score={75} threshold={customThreshold} />);
    
    // Score 75 should be interesting with custom threshold
    const badge = screen.getByText('75').parentElement;
    expect(badge).toHaveClass('bg-amber-100', 'text-amber-800');
    expect(screen.getByText('✨')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    render(<ScoreBadge score={50} className="custom-class" />);
    const badge = screen.getByText('50').parentElement;
    expect(badge).toHaveClass('custom-class');
  });
});