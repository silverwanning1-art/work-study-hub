import { describe, expect, it } from 'vitest';
import { visibleIn } from './registry';

describe('visibleIn', () => {
	it('shows items of the workspace and global items', () => {
		expect(visibleIn({ workspaces: ['arbeit'] }, 'arbeit')).toBe(true);
		expect(visibleIn({ workspaces: ['global'] }, 'studium')).toBe(true);
		expect(visibleIn({ workspaces: ['arbeit'] }, 'studium')).toBe(false);
	});
});
