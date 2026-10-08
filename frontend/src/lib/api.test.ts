import { describe, expect, it, vi } from 'vitest';
import { ApiError, callPluginTool, callTool, confirm, requestPluginWrite, requestWrite } from './api';

function respond(status: number, body: unknown): typeof fetch {
	return vi.fn(async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;
}

describe('callTool', () => {
	it('returns the structured result', async () => {
		const fetchFn = respond(200, { text: [], structured: { ok: 1 }, is_error: false });
		expect(await callTool('get_profile', {}, fetchFn)).toEqual({ ok: 1 });
	});

	it('turns tool errors into the readable message', async () => {
		const fetchFn = respond(200, { text: ['Rechnung unvollständig: x'], structured: null, is_error: true });
		await expect(callTool('issue_invoice', {}, fetchFn)).rejects.toThrow('Rechnung unvollständig: x');
	});

	it('reports an unreachable plugin', async () => {
		await expect(callTool('x', {}, respond(502, {}))).rejects.toThrow(/nicht erreichbar/);
	});
});

describe('writing tools', () => {
	it('requestWrite returns the confirmation id from a 202', async () => {
		const fetchFn = respond(202, { confirmation_id: 'abc' });
		expect(await requestWrite('issue_invoice', { invoice_id: 1 }, fetchFn)).toBe('abc');
	});

	it('requestWrite refuses a response that executed immediately', async () => {
		const fetchFn = respond(200, { text: [], structured: {}, is_error: false });
		await expect(requestWrite('issue_invoice', {}, fetchFn)).rejects.toBeInstanceOf(ApiError);
	});

	it('confirm explains an expired confirmation', async () => {
		await expect(confirm('abc', respond(404, {}))).rejects.toThrow(/abgelaufen/);
	});

	it('confirm returns the result', async () => {
		const fetchFn = respond(200, { text: [], structured: { number: '2026-0001' }, is_error: false });
		expect(await confirm('abc', fetchFn)).toEqual({ number: '2026-0001' });
	});
});

describe('callPluginTool', () => {
	it('calls the given plugin and unwraps the structured result', async () => {
		const fetchFn = respond(200, { text: [], structured: { result: ['a.md'] }, is_error: false });
		expect(await callPluginTool('source-vault', 'list_notes', {}, fetchFn)).toEqual({ result: ['a.md'] });
		const url = (fetchFn as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
		expect(url).toBe('/api/plugins/source-vault/tools/list_notes/call');
	});

	it('names the unreachable plugin', async () => {
		await expect(callPluginTool('source-vault', 'search', {}, respond(502, {}))).rejects.toThrow(/source-vault/);
	});
});

describe('requestPluginWrite', () => {
	it('targets the given plugin and returns the confirmation id', async () => {
		const fetchFn = respond(202, { confirmation_id: 'z' });
		expect(await requestPluginWrite('action-study', 'save_cards', { a: 1 }, fetchFn)).toBe('z');
		const url = (fetchFn as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
		expect(url).toBe('/api/plugins/action-study/tools/save_cards/call');
	});

	it('refuses a response that executed immediately', async () => {
		await expect(requestPluginWrite('action-study', 'save_cards', {}, respond(200, {}))).rejects.toThrow(ApiError);
	});
});
