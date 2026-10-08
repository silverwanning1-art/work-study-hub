<script lang="ts">
	import { onMount } from 'svelte';
	import { loadRegistry, visibleIn, type Registry } from '$lib/registry';

	let registry: Registry | null = $state(null);
	let failed = $state(false);

	onMount(async () => {
		try {
			localStorage.setItem('hub.workspace', 'studium');
		} catch {
			// Not persisting is acceptable.
		}
		try {
			registry = await loadRegistry();
		} catch {
			failed = true;
		}
	});
</script>

<h2>Studium</h2>
<nav aria-label="Studium">
	<a href="/studium/chat">Lern-Coach</a> |
	<a href="/studium/karteikarten">Karteikarten</a> |
	<a href="/studium/vault">Vault</a>
</nav>
{#if failed}
	<p role="alert" class="error">Der Kern ist nicht erreichbar.</p>
{:else if registry === null}
	<p>Lade …</p>
{:else}
	<h3>Plugins</h3>
	<ul>
		{#each registry.plugins.filter((p) => visibleIn(p, 'studium')) as plugin (plugin.id)}
			<li>
				<strong>{plugin.id}</strong>
				<small>{plugin.type} {plugin.version}</small> – {plugin.description}
			</li>
		{:else}
			<li>Keine Plugins in diesem Workspace.</li>
		{/each}
	</ul>
	<h3>Agenten</h3>
	<ul>
		{#each registry.agents.filter((a) => visibleIn(a, 'studium')) as agent (agent.id)}
			<li><strong>{agent.id}</strong> – {agent.description}</li>
		{:else}
			<li>Keine Agenten in diesem Workspace.</li>
		{/each}
	</ul>
{/if}
