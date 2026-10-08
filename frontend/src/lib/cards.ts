/** Flashcards: types, the draft the agent produces, and helpers for the learning mode. */

import { sendChat } from './chat';

export interface Card {
	id: number;
	deck_id: number;
	front: string;
	back: string;
	source_citation: string;
	source_path: string;
	due: string;
	interval_days: number;
	reps: number;
	lapses: number;
}

export interface Deck {
	id: number;
	name: string;
	subject: string;
	card_count: number;
	due_count: number;
}

export interface Stats {
	deck_count: number;
	card_count: number;
	due_today: number;
	reviewed_today: number;
	retention_percent: number | null;
}

export interface DraftCard {
	front: string;
	back: string;
	source_citation: string;
	source_path: string;
}

export interface Draft {
	deck_name: string;
	subject: string;
	cards: DraftCard[];
}

export const PLUGIN = 'action-study';
export const LIMITS = { text: 2000, citation: 300, path: 500, name: 200, cards: 100 } as const;

export const ratings = [
	{ value: 1, label: 'Nochmal' },
	{ value: 2, label: 'Schwer' },
	{ value: 3, label: 'Gut' },
	{ value: 4, label: 'Leicht' }
] as const;

export class DraftError extends Error {}

function text(value: unknown, max: number, required: boolean): string {
	if (value === undefined || value === null) value = '';
	if (typeof value !== 'string') throw new DraftError('Der Entwurf hat ein falsches Format.');
	const trimmed = value.trim();
	if ((required && trimmed === '') || trimmed.length > max) {
		throw new DraftError('Der Entwurf enthält leere oder zu lange Felder.');
	}
	return trimmed;
}

/** Extract and validate the JSON block the skill `karteikarten-erstellen` produces. */
export function parseDraft(answer: string): Draft {
	const match = /```json\s*([\s\S]*?)```/.exec(answer);
	if (!match) throw new DraftError('Der Lern-Coach hat keinen Kartenentwurf geliefert.');
	let data: unknown;
	try {
		data = JSON.parse(match[1]);
	} catch {
		throw new DraftError('Der Kartenentwurf ist kein gültiges JSON.');
	}
	if (typeof data !== 'object' || data === null || !Array.isArray((data as Draft).cards)) {
		throw new DraftError('Der Entwurf hat ein falsches Format.');
	}
	const raw = data as { deck_name?: unknown; subject?: unknown; cards: unknown[] };
	if (raw.cards.length === 0 || raw.cards.length > LIMITS.cards) {
		throw new DraftError(`Der Entwurf muss 1 bis ${LIMITS.cards} Karten enthalten.`);
	}
	const cards = raw.cards.map((entry) => {
		if (typeof entry !== 'object' || entry === null) throw new DraftError('Der Entwurf hat ein falsches Format.');
		const card = entry as Record<string, unknown>;
		return {
			front: text(card.front, LIMITS.text, true),
			back: text(card.back, LIMITS.text, true),
			source_citation: text(card.source_citation, LIMITS.citation, false),
			source_path: text(card.source_path, LIMITS.path, false)
		};
	});
	return {
		deck_name: text(raw.deck_name, LIMITS.name, false),
		subject: text(raw.subject, LIMITS.name, false),
		cards
	};
}

/** Ask the Lern-Coach for a card draft on a topic. The user reviews it before anything is saved. */
export async function generateDraft(
	topic: string,
	count: number,
	fetchFn: typeof fetch = fetch
): Promise<Draft> {
	const prompt =
		`Nutze den Skill karteikarten-erstellen. Thema oder Skript: ${topic.trim()}. ` +
		`Anzahl Karten: ${count}.`;
	const result = await sendChat('lern-coach', [{ role: 'user', content: prompt }], fetchFn);
	return parseDraft(result.answer);
}

/** Cards of a deck the user wants to keep, ready for `save_cards`. */
export function cardsToSave(cards: (DraftCard & { keep: boolean })[]): DraftCard[] {
	return cards
		.filter((c) => c.keep && c.front.trim() !== '' && c.back.trim() !== '')
		.map(({ front, back, source_citation, source_path }) => ({
			front: front.trim(),
			back: back.trim(),
			source_citation,
			source_path
		}));
}
