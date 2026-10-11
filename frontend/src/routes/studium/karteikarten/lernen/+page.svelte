<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { ApiError, callPluginTool } from '$lib/api';
	import { PLUGIN, ratings, type Card } from '$lib/cards';

	let queue: Card[] = $state([]);
	let total = $state(0);
	let revealed = $state(false);
	let loaded = $state(false);
	let busy = $state(false);
	let error: string | null = $state(null);

	let current = $derived(queue[0] ?? null);
	let done = $derived(total - queue.length);

	onMount(async () => {
		const deck = Number(page.url.searchParams.get('deck'));
		const args: Record<string, unknown> = { limit: 50 };
		if (Number.isInteger(deck) && deck > 0) args.deck_id = deck;
		try {
			const result = await callPluginTool<{ cards: Card[] }>(PLUGIN, 'get_due_cards', args);
			queue = result.cards;
			total = result.cards.length;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Der Kern ist nicht erreichbar.';
		} finally {
			loaded = true;
		}
	});

	async function rate(value: number) {
		if (!current || busy) return;
		busy = true;
		error = null;
		try {
			await callPluginTool(PLUGIN, 'rate_card', { card_id: current.id, rating: value });
			queue = queue.slice(1);
			revealed = false;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Der Kern ist nicht erreichbar.';
		} finally {
			busy = false;
		}
	}

	function onKeydown(event: KeyboardEvent) {
		if (!current) return;
		if (!revealed && (event.key === ' ' || event.key === 'Enter')) {
			event.preventDefault();
			revealed = true;
		} else if (revealed && ['1', '2', '3', '4'].includes(event.key)) {
			rate(Number(event.key));
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

<h2>Lernen</h2>
<p><a href="/studium/karteikarten">Zurück zu den Karteikarten</a></p>

{#if error}
	<p role="alert" class="error">{error}</p>
{/if}

{#if !loaded}
	<p>Lade …</p>
{:else if current}
	<p class="muted">Karte {done + 1} von {total}</p>
	<section class="card" aria-live="polite">
		<p class="side">{current.front}</p>
		{#if revealed}
			<hr />
			<p class="side">{current.back}</p>
			{#if current.source_citation}<small class="muted">{current.source_citation}</small>{/if}
		{/if}
	</section>
	{#if revealed}
		<div class="row">
			{#each ratings as r (r.value)}
				<button type="button" onclick={() => rate(r.value)} disabled={busy}>{r.value} {r.label}</button>
			{/each}
		</div>
	{:else}
		<button type="button" class="primary" onclick={() => (revealed = true)}>Antwort zeigen</button>
		<small class="muted"> Leertaste zeigt die Antwort, 1 bis 4 bewertet.</small>
	{/if}
{:else}
	<p role="status">{total === 0 ? 'Heute ist nichts fällig.' : `Fertig: ${total} Karten gelernt.`}</p>
{/if}

<style>
	.card {
		background: #fff;
		border: 1px solid #ddd;
		border-radius: 8px;
		padding: 1rem 1.25rem;
		margin: 0.75rem 0;
		max-width: 40rem;
	}
	.side {
		white-space: pre-wrap;
		font-size: 1.1rem;
		margin: 0.25rem 0;
	}
</style>
