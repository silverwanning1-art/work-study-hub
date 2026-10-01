<script lang="ts">
	import { onMount } from 'svelte';
	import { loadRegistry, visibleIn, type Registry, type Workspace } from '$lib/registry';

	const workspaces: { id: Workspace; label: string }[] = [
		{ id: 'studium', label: 'Studium' },
		{ id: 'arbeit', label: 'Arbeit' }
	];

	let workspace: Workspace = $state('studium');
	let registry: Registry | null = $state(null);
	let failed = $state(false);

	onMount(async () => {
		try {
			const stored = localStorage.getItem('hub.workspace');
			if (stored === 'studium' || stored === 'arbeit') workspace = stored;
		} catch {
			// Storage can be blocked; the default workspace is fine.
		}
		try {
			registry = await loadRegistry();
		} catch {
			failed = true;
		}
	});

	function select(id: Workspace) {
		workspace = id;
		try {
			localStorage.setItem('hub.workspace', id);
		} catch {
			// Not persisting is acceptable.
		}
	}
</script>

<svelte:head>
	<title>Hub</title>
</svelte:head>

<header>
	<h1>Hub</h1>
	<nav aria-label="Workspace">
		{#each workspaces as w (w.id)}
			<button type="button" aria-pressed={workspace === w.id} onclick={() => select(w.id)}>
				{w.label}
			</button>
		{/each}
	</nav>
</header>

<main>
	<h2>{workspaces.find((w) => w.id === workspace)?.label}</h2>
	{#if failed}
		<p role="alert">Der Kern ist nicht erreichbar.</p>
	{:else if registry === null}
		<p>Lade …</p>
	{:else}
		<h3>Plugins</h3>
		<ul>
			{#each registry.plugins.filter((p) => visibleIn(p, workspace)) as plugin (plugin.id)}
				<li><strong>{plugin.id}</strong> <small>{plugin.type} {plugin.version}</small> – {plugin.description}</li>
			{:else}
				<li>Keine Plugins in diesem Workspace.</li>
			{/each}
		</ul>
		<h3>Agenten</h3>
		<ul>
			{#each registry.agents.filter((a) => visibleIn(a, workspace)) as agent (agent.id)}
				<li><strong>{agent.id}</strong> – {agent.description}</li>
			{:else}
				<li>Keine Agenten in diesem Workspace.</li>
			{/each}
		</ul>
	{/if}
</main>

<style>
	:global(body) {
		font-family: system-ui, sans-serif;
		margin: 0;
		color: #1a1a1a;
		background: #fafafa;
	}
	header {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #ddd;
	}
	h1 {
		font-size: 1.25rem;
		margin: 0;
	}
	nav {
		display: flex;
		gap: 0.5rem;
	}
	button {
		padding: 0.4rem 0.9rem;
		border: 1px solid #888;
		border-radius: 6px;
		background: #fff;
		cursor: pointer;
	}
	button[aria-pressed='true'] {
		background: #1a1a1a;
		color: #fff;
	}
	main {
		padding: 1rem;
		max-width: 48rem;
	}
</style>
