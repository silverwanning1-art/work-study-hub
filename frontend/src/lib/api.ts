/** Thin client for the hub core: tool calls with the two-step confirmation for writing tools. */

export class ApiError extends Error {}

interface ToolResult<T> {
	text: string[];
	structured: T | null;
	is_error: boolean;
}

const PLUGIN = 'action-invoice';

async function parse<T>(response: Response): Promise<T> {
	if (!response.ok) {
		throw new ApiError(
			response.status === 502
				? 'Das Rechnungs-Plugin ist nicht erreichbar.'
				: `Anfrage fehlgeschlagen (${response.status}).`
		);
	}
	const result = (await response.json()) as ToolResult<T>;
	if (result.is_error || result.structured === null) {
		throw new ApiError(result.text[0] ?? 'Unbekannter Fehler.');
	}
	return result.structured;
}

function post(url: string, body?: unknown, fetchFn: typeof fetch = fetch): Promise<Response> {
	return fetchFn(url, {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
}

/** Call a non-writing tool and return its structured result. */
export async function callTool<T>(
	tool: string,
	args: Record<string, unknown> = {},
	fetchFn: typeof fetch = fetch
): Promise<T> {
	return parse<T>(await post(`/api/plugins/${PLUGIN}/tools/${tool}/call`, { arguments: args }, fetchFn));
}

/** Ask the core to run a writing tool. Nothing happens until `confirm` is called with the id. */
export async function requestWrite(
	tool: string,
	args: Record<string, unknown>,
	fetchFn: typeof fetch = fetch
): Promise<string> {
	const response = await post(`/api/plugins/${PLUGIN}/tools/${tool}/call`, { arguments: args }, fetchFn);
	if (response.status !== 202) throw new ApiError(`Anfrage fehlgeschlagen (${response.status}).`);
	const body = (await response.json()) as { confirmation_id: string };
	return body.confirmation_id;
}

/** Run a previously requested writing call after the user confirmed it. */
export async function confirm<T>(confirmationId: string, fetchFn: typeof fetch = fetch): Promise<T> {
	const response = await post(`/api/confirmations/${encodeURIComponent(confirmationId)}/confirm`, undefined, fetchFn);
	if (response.status === 404) {
		throw new ApiError('Die Bestätigung ist abgelaufen. Bitte die Aktion erneut starten.');
	}
	return parse<T>(response);
}
