/** Chat with an agent through the core, and helpers to show its sources safely. */

export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;
}

export interface Source {
	citation: string | null;
	path: string | null;
	obsidian_uri: string | null;
}

export interface ToolCall {
	plugin: string;
	tool: string;
	arguments: Record<string, unknown>;
}

export interface ChatResult {
	answer: string;
	sources: Source[];
	tool_calls: ToolCall[];
}

export class ChatError extends Error {}

const STATUS_MESSAGES: Record<number, string> = {
	404: 'Dieser Agent existiert nicht.',
	422: 'Die Nachricht ist ungültig oder zu lang.',
	502: 'Der Agent konnte nicht antworten. Bitte später erneut versuchen.',
	503: 'Der Chat ist nicht eingerichtet: ANTHROPIC_API_KEY fehlt in der .env des Kerns.'
};

/** Send the whole conversation (the core is stateless) and return the agent's answer. */
export async function sendChat(
	agent: string,
	messages: ChatMessage[],
	fetchFn: typeof fetch = fetch
): Promise<ChatResult> {
	const response = await fetchFn(`/api/agents/${encodeURIComponent(agent)}/chat`, {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ messages })
	});
	if (!response.ok) {
		throw new ChatError(STATUS_MESSAGES[response.status] ?? `Anfrage fehlgeschlagen (${response.status}).`);
	}
	return (await response.json()) as ChatResult;
}

/** Only links that open the Obsidian app are rendered as links. */
export function safeObsidianUri(uri: string | null): string | null {
	return uri !== null && uri.startsWith('obsidian://open?') ? uri : null;
}
