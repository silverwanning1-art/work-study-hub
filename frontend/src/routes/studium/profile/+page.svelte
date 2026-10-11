<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, callPluginTool, confirm as confirmWrite, requestPluginWrite } from '$lib/api';
	import { PLUGIN, type Profile } from '$lib/exams';
	import ConfirmDialog from '$lib/ConfirmDialog.svelte';

	const empty = (): Profile => ({
		id: null, name: '', subject: '', description: '', question_style: '',
		share_mc: 40, share_open: 40, share_calc: 20, difficulty: 3, notes: ''
	});

	let profiles: Profile[] = $state([]);
	let form: Profile = $state(empty());
	let loaded = $state(false);
	let busy = $state(false);
	let error: string | null = $state(null);
	let notice: string | null = $state(null);
	let pendingDelete: { id: string; name: string } | null = $state(null);

	let shareSum = $derived(form.share_mc + form.share_open + form.share_calc);
	let valid = $derived(form.name.trim() !== '' && shareSum === 100);

	const describe = (e: unknown) => (e instanceof ApiError ? e.message : 'Der Kern ist nicht erreichbar.');

	async function refresh() {
		try {
			profiles = (await callPluginTool<{ profiles: Profile[] }>(PLUGIN, 'list_profiles')).profiles;
		} catch (e) {
			error = describe(e);
		} finally {
			loaded = true;
		}
	}
	onMount(refresh);

	async function save() {
		if (!valid || busy) return;
		busy = true;
		error = notice = null;
		try {
			await callPluginTool(PLUGIN, 'save_profile', { profile: { ...form, name: form.name.trim() } });
			notice = 'Profil gespeichert.';
			form = empty();
			await refresh();
		} catch (e) {
			error = describe(e);
		} finally {
			busy = false;
		}
	}

	async function askDelete(profile: Profile) {
		error = notice = null;
		try {
			const id = await requestPluginWrite(PLUGIN, 'delete_profile', { profile_id: profile.id });
			pendingDelete = { id, name: profile.name };
		} catch (e) {
			error = describe(e);
		}
	}

	async function onconfirm() {
		if (!pendingDelete) return;
		const id = pendingDelete.id;
		pendingDelete = null;
		try {
			await confirmWrite(id);
			notice = 'Profil gelöscht.';
			await refresh();
		} catch (e) {
			error = describe(e);
		}
	}
</script>

<h2>Prof-Profile</h2>
<p><a href="/studium">Zurück zu Studium</a> | <a href="/studium/pruefungen">Prüfungen</a></p>
<p class="muted">
	Ein Profil beschreibt, wie ein Professor prüft. Daraus erzeugt der Lern-Coach Probeprüfungen im selben Stil.
</p>

{#if error}<p role="alert" class="error">{error}</p>{/if}
{#if notice}<p role="status">{notice}</p>{/if}

{#if !loaded}
	<p>Lade …</p>
{:else}
	<table class="list">
		<thead><tr><th>Name</th><th>Fach</th><th class="num">Schwierigkeit</th><th></th></tr></thead>
		<tbody>
			{#each profiles as profile (profile.id)}
				<tr>
					<td>{profile.name}</td>
					<td>{profile.subject}</td>
					<td class="num">{profile.difficulty} / 5</td>
					<td class="row">
						<button type="button" onclick={() => (form = { ...profile })}>Bearbeiten</button>
						<button type="button" onclick={() => askDelete(profile)}>Löschen</button>
					</td>
				</tr>
			{:else}
				<tr><td colspan="4">Noch keine Profile.</td></tr>
			{/each}
		</tbody>
	</table>
{/if}

<h3>{form.id === null ? 'Neues Profil' : 'Profil bearbeiten'}</h3>
<form
	onsubmit={(event) => {
		event.preventDefault();
		save();
	}}
>
	<label>Name des Professors<input bind:value={form.name} maxlength="200" /></label>
	<label>Fach<input bind:value={form.subject} maxlength="300" /></label>
	<label>
		Beschreibung (frei: Wie prüft die Person, was ist typisch?)
		<textarea bind:value={form.description} rows="5" maxlength="4000"></textarea>
	</label>
	<label>
		Fragestil (z. B. "kurze Definitionsfragen, viele Rechenaufgaben")
		<textarea bind:value={form.question_style} rows="2" maxlength="1000"></textarea>
	</label>
	<div class="row">
		<label>Multiple Choice %<input type="number" min="0" max="100" bind:value={form.share_mc} /></label>
		<label>Offene Fragen %<input type="number" min="0" max="100" bind:value={form.share_open} /></label>
		<label>Rechnen %<input type="number" min="0" max="100" bind:value={form.share_calc} /></label>
	</div>
	{#if shareSum !== 100}<p class="error">Die Anteile ergeben {shareSum}, sie müssen 100 ergeben.</p>{/if}
	<label>Schwierigkeit (1 leicht bis 5 schwer)<input type="number" min="1" max="5" bind:value={form.difficulty} /></label>
	<label>Besonderheiten<textarea bind:value={form.notes} rows="2" maxlength="2000"></textarea></label>
	<button type="submit" class="primary" disabled={!valid || busy}>Speichern</button>
	{#if form.id !== null}<button type="button" onclick={() => (form = empty())}>Abbrechen</button>{/if}
</form>

<ConfirmDialog
	open={pendingDelete !== null}
	title="Profil löschen?"
	message={`Das Profil "${pendingDelete?.name ?? ''}" wird gelöscht. Bereits erstellte Prüfungen bleiben erhalten.`}
	confirmLabel="Löschen"
	{onconfirm}
	oncancel={() => (pendingDelete = null)}
/>
