<script lang="ts">
	import { ApiError, callPluginTool } from '$lib/api';
	import { safeObsidianUri } from '$lib/chat';

	const PLUGIN = 'source-vault';

	interface Hit {
		path: string;
		snippet: string;
		obsidian_uri: string;
	}
	interface Note {
		path: string;
		content: string;
		obsidian_uri: string;
	}

	let query = $state('');
	let hits: Hit[] | null = $state(null);
	let note: Note | null = $state(null);
	let error: string | null = $state(null);
	let busy = $state(false);

	async function run<T>(action: () => Promise<T>): Promise<T | null> {
		error = null;
		busy = true;
		try {
			return await action();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Der Kern ist nicht erreichbar.';
			return null;
		} finally {
			busy = false;
		}
	}

	async function search() {
		if (query.trim() === '') return;
		const result = await run(() =>
			callPluginTool<{ result: Hit[] }>(PLUGIN, 'search', { query, limit: 20 })
		);
		if (result) {
			hits = result.result;
			note = null;
		}
	}

	async function open(path: string) {
		const result = await run(() => callPluginTool<Note>(PLUGIN, 'read_note', { path }));
		if (result) note = result;
	}
</script>

<h2>Vault</h2>
<p><a href="/studium">Zurück zu Studium</a></p>

<form
	onsubmit={(event) => {
		event.preventDefault();
		search();
	}}
>
	<label>
		Suche in den Notizen
		<input bind:value={query} maxlength="200" />
	</label>
	<button type="submit" disabled={busy || query.trim() === ''}>Suchen</button>
</form>

{#if error}
	<p role="alert" class="error">{error}</p>
{/if}

{#if note}
	<h3>{note.path}</h3>
	{#if safeObsidianUri(note.obsidian_uri)}
		<p><a href={safeObsidianUri(note.obsidian_uri)}>In Obsidian öffnen</a></p>
	{/if}
	<pre>{note.content}</pre>
	<button type="button" onclick={() => (note = null)}>Zurück zur Trefferliste</button>
{:else if hits !== null}
	<ul>
		{#each hits as hit (hit.path)}
			<li>
				<button type="button" class="link" onclick={() => open(hit.path)}>{hit.path}</button>
				<br /><small>{hit.snippet}</small>
			</li>
		{:else}
			<li>Keine Treffer.</li>
		{/each}
	</ul>
{/if}

<style>
	pre {
		white-space: pre-wrap;
		background: #fff;
		border: 1px solid #ddd;
		border-radius: 6px;
		padding: 0.75rem;
	}
	.link {
		background: none;
		border: none;
		padding: 0;
		color: #1a56a5;
		text-decoration: underline;
		cursor: pointer;
	}
</style>
