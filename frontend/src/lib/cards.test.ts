import { describe, expect, it, vi } from 'vitest';
import { DraftError, cardsToSave, generateDraft, parseDraft } from './cards';

const valid = {
	deck_name: 'Logistik',
	subject: 'Logistik',
	cards: [{ front: 'Was ist FIFO?', back: 'First in, first out', source_citation: '[Quelle: A.pdf, S. 3]', source_path: 'a/A.pdf' }]
};
const wrap = (value: unknown) => `Hier der Entwurf.\n\`\`\`json\n${JSON.stringify(value)}\n\`\`\``;

describe('parseDraft', () => {
	it('parses a valid draft', () => {
		expect(parseDraft(wrap(valid))).toEqual(valid);
	});

	it('fills optional fields', () => {
		const draft = parseDraft(wrap({ cards: [{ front: 'a', back: 'b' }] }));
		expect(draft.cards[0]).toEqual({ front: 'a', back: 'b', source_citation: '', source_path: '' });
		expect(draft.deck_name).toBe('');
	});

	it.each([
		['no block', 'Kein JSON hier'],
		['broken json', '```json\n{nope\n```'],
		['no cards', wrap({ cards: [] })],
		['cards not array', wrap({ cards: 'x' })],
		['empty front', wrap({ cards: [{ front: ' ', back: 'b' }] })],
		['non-string field', wrap({ cards: [{ front: 1, back: 'b' }] })],
		['too long', wrap({ cards: [{ front: 'x'.repeat(2001), back: 'b' }] })],
		['too many cards', wrap({ cards: Array.from({ length: 101 }, () => ({ front: 'a', back: 'b' })) })]
	])('rejects %s', (_name, answer) => {
		expect(() => parseDraft(answer)).toThrow(DraftError);
	});
});

describe('generateDraft', () => {
	it('asks the lern-coach to use the skill and parses the answer', async () => {
		const fetchFn = vi.fn(async () => new Response(JSON.stringify({ answer: wrap(valid), sources: [], tool_calls: [] }), { status: 200 })) as unknown as typeof fetch;
		expect(await generateDraft('Lagerhaltung', 5, fetchFn)).toEqual(valid);
		const [url, init] = (fetchFn as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
		expect(url).toBe('/api/agents/lern-coach/chat');
		const content = JSON.parse((init as RequestInit).body as string).messages[0].content as string;
		expect(content).toContain('karteikarten-erstellen');
		expect(content).toContain('Lagerhaltung');
	});
});

describe('cardsToSave', () => {
	it('keeps only checked, non-empty cards and trims', () => {
		const cards = [
			{ front: ' a ', back: ' b ', source_citation: 'c', source_path: 'p', keep: true },
			{ front: 'x', back: 'y', source_citation: '', source_path: '', keep: false },
			{ front: ' ', back: 'y', source_citation: '', source_path: '', keep: true }
		];
		expect(cardsToSave(cards)).toEqual([{ front: 'a', back: 'b', source_citation: 'c', source_path: 'p' }]);
	});
});
