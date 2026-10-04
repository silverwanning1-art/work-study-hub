<script lang="ts">
	import { onMount } from 'svelte';
	import { callTool } from '$lib/api';
	import { formatDate, formatEuro } from '$lib/format';
	import { statusLabel, type Customer, type Invoice, type Status } from '$lib/types';

	let invoices: Invoice[] = $state([]);
	let customers: Customer[] = $state([]);
	let filter: Status | '' = $state('');
	let error = $state('');
	let loading = $state(true);

	const customerName = (id: number) => customers.find((c) => c.id === id)?.name ?? '';
	const visible = $derived(filter ? invoices.filter((i) => i.status === filter) : invoices);

	onMount(async () => {
		try {
			localStorage.setItem('hub.workspace', 'arbeit');
		} catch {
			// Not persisting is acceptable.
		}
		try {
			const [inv, cust] = await Promise.all([
				callTool<{ invoices: Invoice[] }>('list_invoices'),
				callTool<{ customers: Customer[] }>('list_customers')
			]);
			invoices = inv.invoices;
			customers = cust.customers;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Fehler beim Laden.';
		} finally {
			loading = false;
		}
	});
</script>

<h2>Arbeit – Rechnungen</h2>

<div class="row">
	<a class="button primary" href="/arbeit/rechnung">Neue Rechnung</a>
	<a class="button" href="/arbeit/stammdaten">Stammdaten</a>
	<label class="row">
		Status
		<select bind:value={filter}>
			<option value="">Alle</option>
			{#each Object.entries(statusLabel) as [value, label] (value)}
				<option {value}>{label}</option>
			{/each}
		</select>
	</label>
</div>

{#if error}
	<p class="error" role="alert">{error}</p>
{:else if loading}
	<p>Lade …</p>
{:else if visible.length === 0}
	<p class="muted">Keine Rechnungen.</p>
{:else}
	<table class="list">
		<thead>
			<tr>
				<th>Nummer</th><th>Kunde</th><th>Datum</th><th>Status</th><th class="num">Brutto</th>
			</tr>
		</thead>
		<tbody>
			{#each visible as invoice (invoice.id)}
				<tr>
					<td>
						<a href={`/arbeit/rechnung?id=${invoice.id}`}>
							{invoice.number ?? 'Entwurf'}{invoice.cancels_number ? ' (Storno)' : ''}
						</a>
					</td>
					<td>{customerName(invoice.customer_id)}</td>
					<td>{formatDate(invoice.issue_date)}</td>
					<td>{statusLabel[invoice.status]}</td>
					<td class="num">{formatEuro(invoice.totals.gross)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
{/if}
