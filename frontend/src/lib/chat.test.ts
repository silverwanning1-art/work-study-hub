import { describe, expect, it, vi } from 'vitest';
import { ChatError, safeObsidianUri, sendChat } from './chat';

function respond(status: number, body: unknown): typeof fetch {
	return vi.fn(async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;
}

describe('sendChat', () => {
	it('posts the conversation and returns the result', async () => {
		const result = { answer: 'Hallo', sources: [], tool_calls: [] };
		const fetchFn = respond(200, result);
		const messages = [{ role: 'user' as const, content: 'Hi' }];
		expect(await sendChat('lern-coach', messages, fetchFn)).toEqual(result);
		const [url, init] = (fetchFn as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
		expect(url).toBe('/api/agents/lern-coach/chat');
		expect(JSON.parse((init as RequestInit).body as string)).toEqual({ messages });
	});

	it.each([
		[503, /ANTHROPIC_API_KEY/],
		[502, /nicht antworten/],
		[404, /existiert nicht/],
		[500, /\(500\)/]
	])('maps status %i to a readable message', async (status, pattern) => {
		await expect(sendChat('x', [], respond(status, {}))).rejects.toThrow(pattern);
		await expect(sendChat('x', [], respond(status, {}))).rejects.toBeInstanceOf(ChatError);
	});
});

describe('safeObsidianUri', () => {
	it('allows obsidian links only', () => {
		expect(safeObsidianUri('obsidian://open?vault=V&file=a')).toBe('obsidian://open?vault=V&file=a');
		expect(safeObsidianUri('javascript:alert(1)')).toBeNull();
		expect(safeObsidianUri('https://evil.example')).toBeNull();
		expect(safeObsidianUri(null)).toBeNull();
	});
});
