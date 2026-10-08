<script lang="ts">
	import { ChatError, safeObsidianUri, sendChat, type ChatMessage, type Source } from '$lib/chat';

	const AGENT = 'lern-coach';

	interface Turn {
		message: ChatMessage;
		sources: Source[];
		tools: string[];
	}

	let turns: Turn[] = $state([]);
	let input = $state('');
	let busy = $state(false);
	let error: string | null = $state(null);

	async function send() {
		const text = input.trim();
		if (!text || busy) return;
		error = null;
		turns.push({ message: { role: 'user', content: text }, sources: [], tools: [] });
		input = '';
		busy = true;
		try {
			const result = await sendChat(
				AGENT,
				turns.map((t) => t.message)
			);
			turns.push({
				message: { role: 'assistant', content: result.answer },
				sources: result.sources,
				tools: result.tool_calls.map((c) => `${c.plugin}.${c.tool}`)
			});
		} catch (e) {
			error = e instanceof ChatError ? e.message : 'Der Kern ist nicht erreichbar.';
		} finally {
			busy = false;
		}
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) send();
	}
</script>

<h2>Lern-Coach</h2>
<p><a href="/studium">Zurück zu Studium</a></p>

<ol class="turns">
	{#each turns as turn, i (i)}
		<li class={turn.message.role}>
			<strong>{turn.message.role === 'user' ? 'Du' : 'Lern-Coach'}</strong>
			<p class="text">{turn.message.content}</p>
			{#if turn.sources.length > 0}
				<details>
					<summary>Quellen ({turn.sources.length})</summary>
					<ul>
						{#each turn.sources as source (source.citation ?? source.path)}
							<li>
								{source.citation ?? source.path}
								{#if safeObsidianUri(source.obsidian_uri)}
									– <a href={safeObsidianUri(source.obsidian_uri)}>in Obsidian öffnen</a>
								{/if}
							</li>
						{/each}
					</ul>
				</details>
			{/if}
			{#if turn.tools.length > 0}
				<small>Genutzt: {turn.tools.join(', ')}</small>
			{/if}
		</li>
	{/each}
</ol>

{#if error}
	<p role="alert" class="error">{error}</p>
{/if}
{#if busy}
	<p>Der Lern-Coach denkt nach …</p>
{/if}

<form
	onsubmit={(event) => {
		event.preventDefault();
		send();
	}}
>
	<label>
		Frage
		<textarea bind:value={input} rows="3" maxlength="8000" onkeydown={onKeydown} disabled={busy}
		></textarea>
	</label>
	<button type="submit" disabled={busy || input.trim() === ''}>Senden</button>
	<small>Strg/Cmd + Enter sendet.</small>
</form>

<style>
	.turns {
		list-style: none;
		padding: 0;
	}
	.turns li {
		margin: 0.75rem 0;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		background: #fff;
		border: 1px solid #ddd;
	}
	.turns li.user {
		background: #eef3fb;
	}
	.text {
		white-space: pre-wrap;
		margin: 0.25rem 0;
	}
</style>
