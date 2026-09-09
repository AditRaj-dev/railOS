import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Modal } from '../ui/Modal';

describe('Modal focus lifecycle', () => {
  it('keeps input focus across parent renders and invokes the latest close callback', () => {
    const firstClose = vi.fn();
    const latestClose = vi.fn();
    const { rerender } = render(
      <Modal open title="Upload" onClose={firstClose}><input aria-label="Caption" /></Modal>,
    );
    const input = screen.getByRole('textbox', { name: 'Caption' });
    input.focus();
    rerender(<Modal open title="Upload" onClose={latestClose}><input aria-label="Caption" /></Modal>);
    expect(input).toHaveFocus();
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(latestClose).toHaveBeenCalledOnce();
    expect(firstClose).not.toHaveBeenCalled();
  });

  it('contains keyboard focus and restores focus when closed', () => {
    const trigger = document.createElement('button');
    document.body.appendChild(trigger);
    trigger.focus();
    const { rerender } = render(<Modal open title="Upload" onClose={vi.fn()}><input aria-label="Caption" /></Modal>);
    const close = screen.getByRole('button', { name: 'Close dialog' });
    const input = screen.getByRole('textbox');
    expect(close).toHaveFocus();
    fireEvent.keyDown(close, { key: 'Tab', shiftKey: true });
    expect(input).toHaveFocus();
    fireEvent.keyDown(input, { key: 'Tab' });
    expect(close).toHaveFocus();
    rerender(<Modal open={false} title="Upload" onClose={vi.fn()}><input aria-label="Caption" /></Modal>);
    expect(trigger).toHaveFocus();
    trigger.remove();
  });
});
