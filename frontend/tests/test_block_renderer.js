/**
 * Unit tests for BlockRenderer
 * Tests pure DOM rendering behavior without state management
 */

describe('BlockRenderer', () => {
  let container;
  let renderer;

  beforeEach(() => {
    // Set up DOM container
    container = document.createElement('div');
    container.id = 'test-transcript';
    document.body.appendChild(container);

    renderer = new BlockRenderer(container);
  });

  afterEach(() => {
    // Clean up
    document.body.removeChild(container);
    renderer = null;
  });

  describe('render()', () => {
    test('should create div element with data-block-id', () => {
      const block = {
        id: 'turn-1-block-1',
        block_type: 'narrator',
        text: 'You notice the silence.',
      };

      const el = renderer.render(block);

      expect(el).toBeInstanceOf(HTMLElement);
      expect(el.tagName).toBe('DIV');
      expect(el.getAttribute('data-block-id')).toBe('turn-1-block-1');
    });

    test('should set data-block-type class', () => {
      const block = {
        id: 'turn-1-block-2',
        block_type: 'actor_line',
        text: 'This is a question.',
      };

      const el = renderer.render(block);

      expect(el.getAttribute('data-block-type')).toBe('actor_line');
      expect(el.className).toContain('scene-block');
      expect(el.className).toContain('scene-block--actor_line');
      expect(el.getAttribute('data-player-visible')).toBe('true');
    });

    test('should set actor_id and target_actor_id attributes when present', () => {
      const block = {
        id: 'turn-1-block-3',
        block_type: 'actor_line',
        actor_id: 'veronique_houllie',
        target_actor_id: 'alain_reille',
        text: 'You are wrong.',
      };

      const el = renderer.render(block);

      expect(el.getAttribute('data-actor-id')).toBe('veronique_houllie');
      expect(el.getAttribute('data-target-actor-id')).toBe('alain_reille');
    });

    test('should set speaker_label attribute when present', () => {
      const block = {
        id: 'turn-1-block-4',
        block_type: 'actor_line',
        speaker_label: 'Véronique',
        text: 'No.',
      };

      const el = renderer.render(block);

      expect(el.getAttribute('data-speaker-label')).toBe('Véronique');
    });

    test('should set text content', () => {
      const text = 'This is the block text.';
      const block = {
        id: 'turn-1-block-5',
        block_type: 'narrator',
        text: text,
      };

      const el = renderer.render(block);

      expect(el.textContent).toBe(text);
    });

    test('should append element to dom_root', () => {
      const block = {
        id: 'turn-1-block-6',
        block_type: 'narrator',
        text: 'Text.',
      };

      expect(container.children.length).toBe(0);

      renderer.render(block);

      expect(container.children.length).toBe(1);
      expect(container.children[0].getAttribute('data-block-id')).toBe('turn-1-block-6');
    });

    test('should render multiple blocks in order', () => {
      const block1 = {
        id: 'turn-1-block-1',
        block_type: 'narrator',
        text: 'First.',
      };
      const block2 = {
        id: 'turn-1-block-2',
        block_type: 'actor_line',
        text: 'Second.',
      };

      renderer.render(block1);
      renderer.render(block2);

      expect(container.children.length).toBe(2);
      expect(container.children[0].getAttribute('data-block-id')).toBe('turn-1-block-1');
      expect(container.children[1].getAttribute('data-block-id')).toBe('turn-1-block-2');
    });

    test('should throw error if block has no id', () => {
      const block = {
        block_type: 'narrator',
        text: 'Text without id.',
      };

      expect(() => renderer.render(block)).toThrow();
    });

    test('should handle block with no text', () => {
      const block = {
        id: 'turn-1-block-7',
        block_type: 'actor_action',
      };

      const el = renderer.render(block);

      expect(el.textContent).toBe('');
    });

    test('should handle block with no block_type', () => {
      const block = {
        id: 'turn-1-block-8',
        text: 'Text.',
      };

      const el = renderer.render(block);

      expect(el.getAttribute('data-block-type')).toBe('unknown');
      expect(el.className).toContain('scene-block--unknown');
    });

    test('should mark dramatic block families as player-visible', () => {
      const dramaticTypes = [
        'narrator_scene',
        'narrator_perception',
        'actor_line',
        'actor_action',
        'stage_shift',
      ];
      for (const kind of dramaticTypes) {
        const el = renderer.render({
          id: `block-${kind}`,
          block_type: kind,
          text: `text-${kind}`,
        });
        expect(el.className).toContain(`scene-block--${kind}`);
        expect(el.getAttribute('data-player-visible')).toBe('true');
        expect(el.textContent).toBe(`text-${kind}`);
      }
    });

    test('should not render diagnostics blocks as player-visible text', () => {
      const el = renderer.render({
        id: 'diag-1',
        block_type: 'diagnostic_trace',
        text: 'internal payload',
      });
      expect(el.getAttribute('data-player-visible')).toBe('false');
      expect(el.className).toContain('scene-block--diagnostic');
      expect(el.textContent).toBe('');
    });
  });

  describe('getBlockElement()', () => {
    test('should retrieve rendered block by id', () => {
      const block = {
        id: 'turn-1-block-1',
        block_type: 'narrator',
        text: 'Text.',
      };

      renderer.render(block);
      const el = renderer.getBlockElement('turn-1-block-1');

      expect(el).toBeTruthy();
      expect(el.getAttribute('data-block-id')).toBe('turn-1-block-1');
    });

    test('should return null if block not found', () => {
      const el = renderer.getBlockElement('nonexistent-id');

      expect(el).toBeNull();
    });

    test('should retrieve correct block among multiple', () => {
      const block1 = { id: 'block-1', block_type: 'narrator', text: 'First.' };
      const block2 = { id: 'block-2', block_type: 'actor_line', text: 'Second.' };
      const block3 = { id: 'block-3', block_type: 'actor_action', text: 'Third.' };

      renderer.render(block1);
      renderer.render(block2);
      renderer.render(block3);

      const el = renderer.getBlockElement('block-2');

      expect(el).toBeTruthy();
      expect(el.textContent).toBe('Second.');
    });
  });

  describe('clear()', () => {
    test('should remove all rendered blocks', () => {
      renderer.render({ id: 'block-1', block_type: 'narrator', text: 'A' });
      renderer.render({ id: 'block-2', block_type: 'narrator', text: 'B' });

      expect(container.children.length).toBe(2);

      renderer.clear();

      expect(container.children.length).toBe(0);
    });

    test('should allow new renders after clear', () => {
      renderer.render({ id: 'block-1', block_type: 'narrator', text: 'A' });
      renderer.clear();
      renderer.render({ id: 'block-2', block_type: 'narrator', text: 'B' });

      expect(container.children.length).toBe(1);
      expect(container.children[0].getAttribute('data-block-id')).toBe('block-2');
    });
  });
});
