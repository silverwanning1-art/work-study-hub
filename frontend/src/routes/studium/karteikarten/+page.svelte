<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, callPluginTool, confirm as confirmWrite, requestPluginWrite } from '$lib/api';
	import { ChatError } from '$lib/chat';
	import {
		DraftError,
		LIMITS,
		PLUGIN,
		cardsToSave,
		generateDraft,
		type Deck,
		type DraftCard,
		type Stats
	} from '$lib/cards';
	import ConfirmDialog from '$lib/ConfirmDialog.svelte';

	type EditableCard = DraftCard & { keep: boolean };

	let decks: Deck[] = $state([]);
	let stats: Stats | null = $state(null);
	let loaded = $state(false);
	let error: string | null = $state(null);
	let notice: string | null = $state(null);
	let busy = $state(false);

	let topic = $state('');
	let count = $state(10);
	let draftName = $state('');
	let draftSubject = $state('');
	let draftCards: EditableCard[] = $state([]);

	let pending: { id: string; title: string; message: string; label: string } | null = $state(null);

	function describe(e: unknown): string {
		if (e instanceof ApiError || e instanceof ChatError || e instanceof DraftError) return e.message;
		return 'Der Kern ist nicht erreichbar.';
	}

	async function refresh() {
		try {
			const [d, s] = await Promise.all([
				callPluginTool<{ decks: Deck[] }>(PLUGIN, 'list_decks'),
				callPluginTool<Stats>(PLUGIN, 'get_stats')
			]);
			decks = d.decks;
			stats = s;
		} catch (e) {
			error = describe(e);
		} finally {
			loaded = true;
		}
	}

	onMount(refresh);

	async function generate() {
		if (topic.trim() === '' || busy) return;
		error = notice = null;
		busy = true;
		try {
			const draft = await generateDraft(topic, count);
			draftName = draft.deck_name || topic.trim().slice(0, LIMITS.name);
			draftSubject = draft.subject;
			draftCards = draft.cards.map((c) => ({ ...c, keep: true }));
		} catch (e) {
			error = describe(e);
		} finally {
			busy = false;
		}
	}

	async function askToSave() {
		const cards = cardsToSave(draftCards);
		if (cards.length === 0 || draftName.trim() === '') return;
		error = notice = null;
		try {
			const id = await requestPluginWrite(PLUGIN, 'save_cards', {
				deck_name: draftName.trim(),
				subject: draftSubject,
				cards
			});
			pending = {
				id,
				title: 'Karten speichern?',
				message: `${cards.length} Karten werden im Stapel "${draftName.trim()}" gespeichert.`,
				label: 'Speichern'
			};
		} catch (e) {
			error = describe(e);
		}
	}

	async function askToDelete(deck: Deck) {
		error = notice = null;
		try {
			const id = await requestPluginWrite(PLUGIN, 'delete_deck', { deck_id: deck.id });
			pending = {
				id,
				title: 'Stapel löschen?',
				message: `Der Stapel "${deck.name}" mit ${deck.card_count} Karten und dem Lernverlauf wird endgültig gelöscht.`,
				label: 'Löschen'
			};
		} catch (e) {
			error = describe(e);
		}
	}

	async function onconfirm() {
		if (!pending) return;
		const id = pending.id;
		const wasSave = pending.label === 'Speichern';
		pending = null;
		try {
			await confirmWrite(id);
			if (wasSave) {
				draftCards = [];
				topic = '';
				notice = 'Karten gespeichert.';
			} else {
				notice = 'Stapel gelöscht.';
			}
			await refresh();
		} catch (e) {
			error = describe(e);
		}
	}
</script>

<h2>Karteikarten</h2>
<p><a href="/studium">Zurück zu Studium</a></p>

{#if error}
	<p role="alert" class="error">{error}</p>
{/if}
{#if notice}
	<p role="status">{notice}</p>
{/if}

{#if stats}
	<p class="muted">
		{stats.card_count} Karten in {stats.deck_count} Stapeln, heute fällig: {stats.due_today}, heute gelernt:
		{stats.reviewed_today}{#if stats.retention_percent !== null}, Behaltensquote (30 Tage): {stats.retention_percent}
			%{/if}
	</p>
{/if}

<h3>Stapel</h3>
{#if !loaded}
	<p>Lade …</p>
{:else}
	<table class="list">
		<thead><tr><th>Stapel</th><th class="num">Karten</th><th class="num">Fällig</th><th></th></tr></thead>
		<tbody>
			{#each decks as deck (deck.id)}
				<tr>
					<td>{deck.name}{#if deck.subject}<small class="muted"> – {deck.subject}</small>{/if}</td>
					<td class="num">{deck.card_count}</td>
					<td class="num">{deck.due_count}</td>
					<td class="row">
						<a class="button" href={`/studium/karteikarten/lernen?deck=${deck.id}`} aria-disabled={deck.due_count === 0}>Lernen</a>
						<button type="button" onclick={() => askToDelete(deck)}>Löschen</button>
					</td>
				</tr>
			{:else}
				<tr><td colspan="4">Noch keine Stapel. Erzeuge unten einen Entwurf.</td></tr>
			{/each}
		</tbody>
	</table>
	{#if decks.length > 0}
		<p><a class="button" href="/studium/karteikarten/lernen">Alle fälligen Karten lernen</a></p>
	{/if}
{/if}

<h3>Neue Karten aus den Skripten</h3>
<form
	onsubmit={(event) => {
		event.preventDefault();
		generate();
	}}
>
	<label>
		Thema oder Skript
		<input bind:value={topic} maxlength="200" placeholder="z. B. Lagerhaltung und Bestellpunktverfahren" />
	</label>
	<label>
		Anzahl Karten
		<input type="number" bind:value={count} min="1" max="30" />
	</label>
	<button type="submit" disabled={busy || topic.trim() === ''}>Entwurf erzeugen</button>
	{#if busy}<small>Der Lern-Coach sucht in den Skripten …</small>{/if}
</form>

{#if draftCards.length > 0}
	<h3>Entwurf prüfen</h3>
	<p class="muted">Nichts ist gespeichert. Streiche oder ändere Karten und speichere dann.</p>
	<label>Stapelname<input bind:value={draftName} maxlength="200" /></label>
	{#each draftCards as card, i (i)}
		<fieldset>
			<label class="row"><input type="checkbox" bind:checked={card.keep} style="width:auto" /> Übernehmen</label>
			<label>Vorderseite<textarea bind:value={card.front} rows="2" maxlength="2000" disabled={!card.keep}></textarea></label>
			<label>Rückseite<textarea bind:value={card.back} rows="3" maxlength="2000" disabled={!card.keep}></textarea></label>
			{#if card.source_citation}<small class="muted">{card.source_citation}</small>{/if}
		</fieldset>
	{/each}
	<button type="button" class="primary" onclick={askToSave} disabled={cardsToSave(draftCards).length === 0 || draftName.trim() === ''}>
		{cardsToSave(draftCards).length} Karten speichern
	</button>
{/if}

<ConfirmDialog
	open={pending !== null}
	title={pending?.title ?? ''}
	message={pending?.message ?? ''}
	confirmLabel={pending?.label ?? ''}
	{onconfirm}
	oncancel={() => (pending = null)}
/>
