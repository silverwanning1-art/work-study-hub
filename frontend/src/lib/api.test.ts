import { describe, expect, it, vi } from 'vitest';
import { ApiError, callTool, confirm, requestWrite } from './api';

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
