<script lang="ts">
	import { onMount } from 'svelte';
	import { callTool } from '$lib/api';
	import type { Customer, Profile, Project } from '$lib/types';

	const emptyCustomer = (): Customer => ({
		id: null,
		name: '',
		street: '',
		postal_code: '',
		city: '',
		country: 'Deutschland',
		vat_id: '',
		email: ''
	});

	const emptyProject = (customerId = 0): Project => ({
		id: null,
		customer_id: customerId,
		name: '',
		notes: ''
	});

	const profileFields: { key: keyof Profile; label: string }[] = [
		{ key: 'name', label: 'Name' },
		{ key: 'street', label: 'Straße und Hausnummer' },
		{ key: 'postal_code', label: 'PLZ' },
		{ key: 'city', label: 'Ort' },
		{ key: 'country', label: 'Land' },
		{ key: 'tax_number', label: 'Steuernummer' },
		{ key: 'vat_id', label: 'USt-IdNr. (falls vorhanden)' },
		{ key: 'email', label: 'E-Mail' },
		{ key: 'phone', label: 'Telefon' },
		{ key: 'bank_name', label: 'Bank' },
		{ key: 'iban', label: 'IBAN' },
		{ key: 'bic', label: 'BIC' }
	];

	let profile = $state<Profile | null>(null);
	let customers = $state<Customer[]>([]);
	let projects = $state<Project[]>([]);
	let customerForm = $state<Customer>(emptyCustomer());
	let projectForm = $state<Project>(emptyProject());
	let error = $state('');
	let info = $state('');
	let busy = $state(false);

	async function refresh() {
		customers = (await callTool<{ customers: Customer[] }>('list_customers')).customers;
		projects = (await callTool<{ projects: Project[] }>('list_projects')).projects;
	}

	async function run(work: () => Promise<void>, message: string) {
		busy = true;
		error = '';
		info = '';
		try {
			await work();
			info = message;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unbekannter Fehler.';
		} finally {
			busy = false;
		}
	}

	onMount(() =>
		run(async () => {
			profile = await callTool<Profile>('get_profile');
			await refresh();
		}, '')
	);

	const saveProfile = () =>
		run(async () => {
			profile = await callTool<Profile>('save_profile', { profile });
		}, 'Stammdaten gespeichert.');

	const saveCustomer = () =>
		run(async () => {
			await callTool('save_customer', { customer: customerForm });
			customerForm = emptyCustomer();
			await refresh();
		}, 'Kunde gespeichert.');

	const saveProject = () =>
		run(async () => {
			await callTool('save_project', { project: projectForm });
			projectForm = emptyProject(projectForm.customer_id);
			await refresh();
		}, 'Projekt gespeichert.');

	const customerName = (id: number) => customers.find((c) => c.id === id)?.name ?? '';
</script>

<p><a href="/arbeit">← Rechnungen</a></p>
<h2>Stammdaten</h2>
{#if error}<p class="error" role="alert">{error}</p>{/if}
{#if info}<p role="status">{info}</p>{/if}

<h3>Meine Angaben (Leistender)</h3>
<p class="muted">
	Diese Angaben stehen auf jeder Rechnung. Ausgestellte Rechnungen behalten den Stand zum Zeitpunkt
	des Ausstellens.
</p>
{#if profile}
	<form
		onsubmit={(event) => {
			event.preventDefault();
			void saveProfile();
		}}
	>
		{#each profileFields as field (field.key)}
			<label>{field.label}
				<input bind:value={profile[field.key] as string} />
			</label>
		{/each}
		<label>Zahlungsziel (Tage)
			<input type="number" min="0" max="365" bind:value={profile.payment_terms_days} />
		</label>
		<label>Hinweistext zur Umsatzsteuer (leer lassen, wenn Umsatzsteuer ausgewiesen wird)
			<textarea rows="3" bind:value={profile.tax_exemption_note}></textarea>
		</label>
		<p class="muted">
			Ist ein Hinweistext gesetzt, werden Rechnungen ohne Umsatzsteuer (0 %) und mit diesem Text
			ausgestellt. Bitte die steuerliche Behandlung mit Steuerberater oder Finanzamt klären.
		</p>
		<button type="submit" class="primary" disabled={busy}>Speichern</button>
	</form>
{/if}

<h3>Kunden</h3>
<table class="list">
	<tbody>
		{#each customers as customer (customer.id)}
			<tr>
				<td>{customer.name}</td>
				<td>{customer.postal_code} {customer.city}</td>
				<td><button type="button" onclick={() => (customerForm = { ...customer })}>Bearbeiten</button></td>
			</tr>
		{:else}
			<tr><td class="muted">Noch keine Kunden.</td></tr>
		{/each}
	</tbody>
</table>
<form
	onsubmit={(event) => {
		event.preventDefault();
		void saveCustomer();
	}}
>
	<h4>{customerForm.id === null ? 'Neuer Kunde' : 'Kunde bearbeiten'}</h4>
	<label>Name <input bind:value={customerForm.name} required /></label>
	<label>Straße und Hausnummer <input bind:value={customerForm.street} /></label>
	<div class="row">
		<label>PLZ <input bind:value={customerForm.postal_code} /></label>
		<label>Ort <input bind:value={customerForm.city} /></label>
		<label>Land <input bind:value={customerForm.country} /></label>
	</div>
	<label>USt-IdNr. (optional) <input bind:value={customerForm.vat_id} /></label>
	<label>E-Mail (optional) <input bind:value={customerForm.email} /></label>
	<div class="row">
		<button type="submit" class="primary" disabled={busy}>Kunde speichern</button>
		{#if customerForm.id !== null}
			<button type="button" onclick={() => (customerForm = emptyCustomer())}>Abbrechen</button>
		{/if}
	</div>
</form>

<h3>Projekte</h3>
<table class="list">
	<tbody>
		{#each projects as project (project.id)}
			<tr>
				<td>{project.name}</td>
				<td>{customerName(project.customer_id)}</td>
				<td><button type="button" onclick={() => (projectForm = { ...project })}>Bearbeiten</button></td>
			</tr>
		{:else}
			<tr><td class="muted">Noch keine Projekte.</td></tr>
		{/each}
	</tbody>
</table>
<form
	onsubmit={(event) => {
		event.preventDefault();
		void saveProject();
	}}
>
	<h4>{projectForm.id === null ? 'Neues Projekt' : 'Projekt bearbeiten'}</h4>
	<label>Kunde
		<select bind:value={projectForm.customer_id} required>
			<option value={0}>– wählen –</option>
			{#each customers as customer (customer.id)}
				<option value={customer.id}>{customer.name}</option>
			{/each}
		</select>
	</label>
	<label>Name <input bind:value={projectForm.name} required /></label>
	<label>Notizen <textarea rows="2" bind:value={projectForm.notes}></textarea></label>
	<div class="row">
		<button type="submit" class="primary" disabled={busy || projectForm.customer_id === 0}>Projekt speichern</button>
		{#if projectForm.id !== null}
			<button type="button" onclick={() => (projectForm = emptyProject())}>Abbrechen</button>
		{/if}
	</div>
</form>
