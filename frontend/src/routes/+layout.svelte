<script lang="ts">
	import { page } from '$app/state';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	const workspaces = [
		{ href: '/studium', label: 'Studium' },
		{ href: '/arbeit', label: 'Arbeit' }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Hub</title>
</svelte:head>

<header>
	<h1>Hub</h1>
	<nav aria-label="Workspace">
		{#each workspaces as w (w.href)}
			<a href={w.href} aria-current={page.url.pathname.startsWith(w.href) ? 'page' : undefined}>
				{w.label}
			</a>
		{/each}
	</nav>
</header>

<main>
	{@render children()}
</main>

<style>
	:global(body) {
		font-family: system-ui, sans-serif;
		margin: 0;
		color: #1a1a1a;
		background: #fafafa;
	}
	:global(h2) {
		margin-top: 0;
	}
	:global(label) {
		display: block;
		margin: 0.5rem 0;
		font-size: 0.9rem;
	}
	:global(input),
	:global(select),
	:global(textarea) {
		display: block;
		width: 100%;
		box-sizing: border-box;
		padding: 0.35rem 0.5rem;
		border: 1px solid #aaa;
		border-radius: 4px;
		font: inherit;
	}
	:global(button),
	:global(a.button) {
		padding: 0.4rem 0.9rem;
		border: 1px solid #888;
		border-radius: 6px;
		background: #fff;
		cursor: pointer;
		font: inherit;
		color: inherit;
		text-decoration: none;
		display: inline-block;
	}
	:global(button.primary) {
		background: #1a1a1a;
		color: #fff;
	}
	:global(button:disabled) {
		opacity: 0.5;
		cursor: not-allowed;
	}
	:global(.error) {
		color: #9b1c1c;
		background: #fdecec;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
	}
	:global(.muted) {
		color: #666;
	}
	:global(table.list) {
		width: 100%;
		border-collapse: collapse;
	}
	:global(table.list th),
	:global(table.list td) {
		text-align: left;
		padding: 0.4rem 0.5rem;
		border-bottom: 1px solid #ddd;
	}
	:global(.num) {
		text-align: right !important;
		white-space: nowrap;
	}
	:global(.row) {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		flex-wrap: wrap;
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
	nav a {
		padding: 0.4rem 0.9rem;
		border: 1px solid #888;
		border-radius: 6px;
		background: #fff;
		color: inherit;
		text-decoration: none;
	}
	nav a[aria-current='page'] {
		background: #1a1a1a;
		color: #fff;
	}
	main {
		padding: 1rem;
		max-width: 56rem;
	}
</style>
