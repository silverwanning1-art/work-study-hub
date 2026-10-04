<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { callTool, confirm as confirmWrite, requestWrite } from '$lib/api';
	import ConfirmDialog from '$lib/ConfirmDialog.svelte';
	import { formatDate, formatEuro, parseDecimal, toInputDecimal } from '$lib/format';
	import { statusLabel, type Customer, type Invoice, type Project } from '$lib/types';

	interface FormItem {
		description: string;
		quantity: string;
		unit: string;
		unit_price: string;
		tax_rate_percent: number;
	}

	interface Form {
		id: number | null;
		customer_id: number | null;
		project_id: number | null;
		issue_date: string;
		service_start: string;
		service_end: string;
		note: string;
		items: FormItem[];
	}

	type ActionKind = 'issue' | 'paid' | 'cancel';

	const actions: Record<
		ActionKind,
		{ tool: string; title: string; message: string; label: string }
	> = {
		issue: {
			tool: 'issue_invoice',
			title: 'Rechnung ausstellen?',
			message:
				'Es wird die nächste Rechnungsnummer vergeben und das PDF erzeugt. Danach ist die Rechnung unveränderlich; Korrekturen sind nur per Stornorechnung möglich.',
			label: 'Ausstellen'
		},
		paid: {
			tool: 'mark_paid',
			title: 'Als bezahlt markieren?',
			message: 'Die Rechnung wird als bezahlt vermerkt (heutiges Datum).',
			label: 'Als bezahlt markieren'
		},
		cancel: {
			tool: 'cancel_invoice',
			title: 'Rechnung stornieren?',
			message:
				'Es wird eine Stornorechnung mit eigener Nummer erzeugt. Die ursprüngliche Rechnung gilt danach als storniert. Das kann nicht rückgängig gemacht werden.',
			label: 'Stornieren'
		}
	};

	const emptyItem = (): FormItem => ({
		description: '',
		quantity: '1',
		unit: 'Std.',
		unit_price: '',
		tax_rate_percent: 19
	});

	const emptyForm = (): Form => ({
		id: null,
		customer_id: null,
		project_id: null,
		issue_date: '',
		service_start: '',
		service_end: '',
		note: '',
		items: [emptyItem()]
	});

	let customers: Customer[] = $state([]);
	let projects: Project[] = $state([]);
	let invoice = $state<Invoice | null>(null);
	let form: Form = $state(emptyForm());
	let savedForm = $state(JSON.stringify(emptyForm()));
	let error = $state('');
	let info = $state('');
	let busy = $state(false);
	let pending = $state<{ kind: ActionKind; confirmationId: string } | null>(null);

	const dirty = $derived(JSON.stringify(form) !== savedForm);
	const isDraft = $derived(invoice === null || invoice.status === 'draft');
	const customerName = (id: number) => customers.find((c) => c.id === id)?.name ?? '';

	function toForm(inv: Invoice): Form {
		return {
			id: inv.id,
			customer_id: inv.customer_id,
			project_id: inv.project_id,
			issue_date: inv.issue_date ?? '',
			service_start: inv.service_start ?? '',
			service_end: inv.service_end ?? '',
			note: inv.note,
			items: inv.items.map((i) => ({
				description: i.description,
				quantity: toInputDecimal(i.quantity),
				unit: i.unit,
				unit_price: toInputDecimal(i.unit_price),
				tax_rate_percent: i.tax_rate_percent
			}))
		};
	}

	function remember(next: Form) {
		form = next;
		savedForm = JSON.stringify(next);
	}

	function toPayload(f: Form) {
		if (f.customer_id === null) throw new Error('Bitte einen Kunden wählen.');
		const items = f.items.map((item, index) => {
			const quantity = parseDecimal(item.quantity);
			const unitPrice = parseDecimal(item.unit_price);
			if (quantity === null) throw new Error(`Position ${index + 1}: Menge ist keine Zahl.`);
			if (unitPrice === null) throw new Error(`Position ${index + 1}: Einzelpreis ist keine Zahl.`);
			return {
				description: item.description,
				quantity,
				unit: item.unit,
				unit_price: unitPrice,
				tax_rate_percent: item.tax_rate_percent
			};
		});
		return {
			id: f.id,
			customer_id: f.customer_id,
			project_id: f.project_id,
			issue_date: f.issue_date || null,
			service_start: f.service_start || null,
			service_end: f.service_end || null,
			note: f.note,
			items
		};
	}

	async function loadProjects(customerId: number | null) {
		projects =
			customerId === null
				? []
				: (await callTool<{ projects: Project[] }>('list_projects', { customer_id: customerId }))
						.projects;
	}

	async function load(id: string | null) {
		error = '';
		info = '';
		try {
			if (customers.length === 0) {
				customers = (await callTool<{ customers: Customer[] }>('list_customers')).customers;
			}
			if (id === null) {
				invoice = null;
				remember(emptyForm());
				projects = [];
				return;
			}
			const loaded = await callTool<Invoice>('get_invoice', { invoice_id: Number(id) });
			invoice = loaded;
			remember(toForm(loaded));
			await loadProjects(loaded.customer_id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Fehler beim Laden.';
		}
	}

	$effect(() => {
		void load(page.url.searchParams.get('id'));
	});

	async function onCustomerChange() {
		form.project_id = null;
		try {
			await loadProjects(form.customer_id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Fehler beim Laden.';
		}
	}

	async function run<T>(work: () => Promise<T>): Promise<T | undefined> {
		busy = true;
		error = '';
		info = '';
		try {
			return await work();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unbekannter Fehler.';
			return undefined;
		} finally {
			busy = false;
		}
	}

	async function save() {
		const saved = await run(() =>
			callTool<Invoice>('save_invoice_draft', { draft: toPayload(form) })
		);
		if (!saved) return;
		invoice = saved;
		remember(toForm(saved));
		info = 'Entwurf gespeichert.';
		if (page.url.searchParams.get('id') !== String(saved.id)) {
			await goto(`/arbeit/rechnung?id=${saved.id}`, { replaceState: true, noScroll: true });
		}
	}

	async function removeDraft() {
		if (!invoice || !window.confirm('Entwurf endgültig löschen?')) return;
		const done = await run(() => callTool('delete_invoice_draft', { invoice_id: invoice!.id }));
		if (done) await goto('/arbeit');
	}

	async function startAction(kind: ActionKind) {
		if (!invoice) return;
		const id = invoice.id;
		const confirmationId = await run(() => requestWrite(actions[kind].tool, { invoice_id: id }));
		if (confirmationId) pending = { kind, confirmationId };
	}

	async function runPending() {
		if (!pending) return;
		const { kind, confirmationId } = pending;
		pending = null;
		const result = await run(() => confirmWrite<Invoice>(confirmationId));
		if (!result) return;
		invoice = result;
		remember(toForm(result));
		info =
			kind === 'issue'
				? `Rechnung ${result.number} ausgestellt.`
				: kind === 'paid'
					? 'Als bezahlt markiert.'
					: `Stornorechnung ${result.number} erstellt.`;
		await goto(`/arbeit/rechnung?id=${result.id}`, { replaceState: true, noScroll: true });
	}
</script>

<p><a href="/arbeit">← Alle Rechnungen</a></p>
<h2>
	{#if invoice === null}Neue Rechnung{:else if invoice.number}{invoice.cancels_number
			? 'Stornorechnung'
			: 'Rechnung'} {invoice.number}{:else}Entwurf{/if}
	{#if invoice}<small class="muted">({statusLabel[invoice.status]})</small>{/if}
</h2>

{#if error}<p class="error" role="alert">{error}</p>{/if}
{#if info}<p role="status">{info}</p>{/if}

{#if isDraft}
	<form
		onsubmit={(event) => {
			event.preventDefault();
			void save();
		}}
	>
		<label>
			Kunde
			<select bind:value={form.customer_id} onchange={onCustomerChange}>
				<option value={null}>– wählen –</option>
				{#each customers as customer (customer.id)}
					<option value={customer.id}>{customer.name}</option>
				{/each}
			</select>
		</label>
		<p class="muted"><a href="/arbeit/stammdaten">Kunden und Projekte verwalten</a></p>
		<label>
			Projekt (optional)
			<select bind:value={form.project_id} disabled={form.customer_id === null}>
				<option value={null}>– keines –</option>
				{#each projects as project (project.id)}
					<option value={project.id}>{project.name}</option>
				{/each}
			</select>
		</label>
		<div class="row">
			<label>Rechnungsdatum (leer = Tag des Ausstellens)
				<input type="date" bind:value={form.issue_date} />
			</label>
			<label>Leistung von
				<input type="date" bind:value={form.service_start} />
			</label>
			<label>Leistung bis
				<input type="date" bind:value={form.service_end} />
			</label>
		</div>

		<table class="list">
			<thead>
				<tr>
					<th>Beschreibung</th><th>Menge</th><th>Einheit</th><th>Einzelpreis (€)</th><th>USt</th><th></th>
				</tr>
			</thead>
			<tbody>
				{#each form.items as item, index (index)}
					<tr>
						<td><input bind:value={item.description} aria-label="Beschreibung" /></td>
						<td><input bind:value={item.quantity} inputmode="decimal" aria-label="Menge" /></td>
						<td><input bind:value={item.unit} aria-label="Einheit" /></td>
						<td><input bind:value={item.unit_price} inputmode="decimal" aria-label="Einzelpreis" /></td>
						<td>
							<select bind:value={item.tax_rate_percent} aria-label="Umsatzsteuer">
								<option value={19}>19 %</option>
								<option value={7}>7 %</option>
								<option value={0}>0 %</option>
							</select>
						</td>
						<td>
							<button
								type="button"
								onclick={() => form.items.splice(index, 1)}
								disabled={form.items.length === 1}
								aria-label="Position entfernen">✕</button
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<p><button type="button" onclick={() => form.items.push(emptyItem())}>+ Position</button></p>

		<label>Hinweis auf der Rechnung (optional)
			<textarea rows="3" bind:value={form.note}></textarea>
		</label>

		<div class="row">
			<button type="submit" class="primary" disabled={busy || !dirty}>Entwurf speichern</button>
			{#if invoice}
				<button
					type="button"
					class="primary"
					disabled={busy || dirty}
					title={dirty ? 'Bitte zuerst speichern' : ''}
					onclick={() => startAction('issue')}>Ausstellen …</button
				>
				<button type="button" disabled={busy} onclick={removeDraft}>Entwurf löschen</button>
			{/if}
		</div>
	</form>

	{#if invoice}
		<h3>Summen (laut gespeichertem Entwurf)</h3>
		<table class="list">
			<tbody>
				<tr><td>Netto</td><td class="num">{formatEuro(invoice.totals.net)}</td></tr>
				{#each invoice.totals.tax_lines.filter((l) => l.tax_rate_percent > 0) as line (line.tax_rate_percent)}
					<tr><td>USt {line.tax_rate_percent} %</td><td class="num">{formatEuro(line.tax)}</td></tr>
				{/each}
				<tr><td><strong>Brutto</strong></td><td class="num"><strong>{formatEuro(invoice.totals.gross)}</strong></td></tr>
			</tbody>
		</table>
		<p class="muted">
			Die Umsatzsteuer richtet sich nach den Stammdaten (Hinweistext auf Steuerbefreiung
			gesetzt = 0 %).
		</p>
	{/if}
{:else if invoice}
	<p>
		{customerName(invoice.customer_id)} · Datum {formatDate(invoice.issue_date)} · Leistung
		{formatDate(invoice.service_start)}{invoice.service_end !== invoice.service_start
			? ` – ${formatDate(invoice.service_end)}`
			: ''}
		{#if invoice.cancels_number}· Storno zu Rechnung {invoice.cancels_number}{/if}
	</p>
	<table class="list">
		<thead>
			<tr><th>Pos.</th><th>Beschreibung</th><th class="num">Menge</th><th>Einheit</th><th class="num">Einzelpreis</th><th class="num">USt</th><th class="num">Netto</th></tr>
		</thead>
		<tbody>
			{#each invoice.items as item (item.position)}
				<tr>
					<td>{item.position}</td><td>{item.description}</td>
					<td class="num">{toInputDecimal(item.quantity)}</td><td>{item.unit}</td>
					<td class="num">{formatEuro(item.unit_price)}</td>
					<td class="num">{item.tax_rate_percent} %</td>
					<td class="num">{formatEuro(item.net)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	<table class="list">
		<tbody>
			<tr><td>Netto</td><td class="num">{formatEuro(invoice.totals.net)}</td></tr>
			{#each invoice.totals.tax_lines.filter((l) => l.tax_rate_percent > 0) as line (line.tax_rate_percent)}
				<tr><td>USt {line.tax_rate_percent} %</td><td class="num">{formatEuro(line.tax)}</td></tr>
			{/each}
			<tr><td><strong>Brutto</strong></td><td class="num"><strong>{formatEuro(invoice.totals.gross)}</strong></td></tr>
		</tbody>
	</table>
	{#if invoice.tax_exemption_note}<p>{invoice.tax_exemption_note}</p>{/if}
	{#if invoice.note}<p>{invoice.note}</p>{/if}

	<div class="row">
		<a class="button primary" data-sveltekit-reload href={`/api/invoices/${invoice.id}/pdf`}>PDF herunterladen</a>
		{#if invoice.status === 'issued' && !invoice.cancels_number}
			<button type="button" disabled={busy} onclick={() => startAction('paid')}>Als bezahlt markieren …</button>
		{/if}
		{#if (invoice.status === 'issued' || invoice.status === 'paid') && !invoice.cancels_number}
			<button type="button" disabled={busy} onclick={() => startAction('cancel')}>Stornieren …</button>
		{/if}
	</div>
{/if}

<ConfirmDialog
	open={pending !== null}
	title={pending ? actions[pending.kind].title : ''}
	message={pending ? actions[pending.kind].message : ''}
	confirmLabel={pending ? actions[pending.kind].label : ''}
	onconfirm={runPending}
	oncancel={() => (pending = null)}
/>
