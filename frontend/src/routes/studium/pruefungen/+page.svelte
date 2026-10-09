<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, callPluginTool, confirm as confirmWrite, requestPluginWrite } from '$lib/api';
	import { ChatError } from '$lib/chat';
	import {
		ExamError, PLUGIN, generateExamDraft, kindLabel, questionsToSave,
		type DraftQuestion, type ExamSummary, type Profile
	} from '$lib/exams';
	import ConfirmDialog from '$lib/ConfirmDialog.svelte';

	type Editable = DraftQuestion & { keep: boolean };

	let exams: ExamSummary[] = $state([]);
	let profiles: Profile[] = $state([]);
	let loaded = $state(false);
	let busy = $state(false);
	let error: string | null = $state(null);
	let notice: string | null = $state(null);

	let profileId: number | '' = $state('');
	let subject = $state('');
	let topics = $state('');
	let count = $state(10);

	let title = $state('');
	let draft: Editable[] = $state([]);
	let draftProfile: number | null = $state(null);
	let draftSubject = $state('');
	let pending: { id: string; title: string; message: string; label: string } | null = $state(null);

	let keptPoints = $derived(questionsToSave(draft).reduce((sum, q) => sum + q.points, 0));

	function describe(e: unknown): string {
		if (e instanceof ApiError || e instanceof ChatError || e instanceof ExamError) return e.message;
		return 'Der Kern ist nicht erreichbar.';
	}

	async function refresh() {
		try {
			const [e, p] = await Promise.all([
				callPluginTool<{ exams: ExamSummary[] }>(PLUGIN, 'list_exams'),
				callPluginTool<{ profiles: Profile[] }>(PLUGIN, 'list_profiles')
			]);
			exams = e.exams;
			profiles = p.profiles;
		} catch (e) {
			error = describe(e);
		} finally {
			loaded = true;
		}
	}
	onMount(refresh);

	async function generate() {
		const profile = profiles.find((p) => p.id === profileId);
		if (!profile || busy) return;
		error = notice = null;
		busy = true;
		try {
			const result = await generateExamDraft(profile, subject, topics, count);
			title = result.title || `Probeprüfung ${profile.subject || profile.name}`;
			draftSubject = result.subject || subject || profile.subject;
			draftProfile = profile.id;
			draft = result.questions.map((q) => ({ ...q, keep: true }));
		} catch (e) {
			error = describe(e);
		} finally {
			busy = false;
		}
	}

	async function askSave() {
		const questions = questionsToSave(draft);
		if (questions.length === 0 || title.trim() === '') return;
		error = notice = null;
		try {
			const id = await requestPluginWrite(PLUGIN, 'save_exam', {
				exam: { title: title.trim(), subject: draftSubject, profile_id: draftProfile, questions }
			});
			pending = {
				id, label: 'Speichern', title: 'Prüfung speichern?',
				message: `Die Prüfung "${title.trim()}" mit ${questions.length} Fragen (${keptPoints} Punkte) wird gespeichert.`
			};
		} catch (e) {
			error = describe(e);
		}
	}

	async function askDelete(exam: ExamSummary) {
		error = notice = null;
		try {
			const id = await requestPluginWrite(PLUGIN, 'delete_exam', { exam_id: exam.id });
			pending = {
				id, label: 'Löschen', title: 'Prüfung löschen?',
				message: `Die Prüfung "${exam.title}" mit ${exam.attempt_count} Durchführungen wird endgültig gelöscht.`
			};
		} catch (e) {
			error = describe(e);
		}
	}

	async function onconfirm() {
		if (!pending) return;
		const { id, label } = pending;
		pending = null;
		try {
			await confirmWrite(id);
			if (label === 'Speichern') {
				draft = [];
				notice = 'Prüfung gespeichert.';
			} else {
				notice = 'Prüfung gelöscht.';
			}
			await refresh();
		} catch (e) {
			error = describe(e);
		}
	}
</script>

<h2>Probeprüfungen</h2>
<p><a href="/studium">Zurück zu Studium</a> | <a href="/studium/profile">Prof-Profile</a></p>

{#if error}<p role="alert" class="error">{error}</p>{/if}
{#if notice}<p role="status">{notice}</p>{/if}

<h3>Gespeicherte Prüfungen</h3>
{#if !loaded}
	<p>Lade …</p>
{:else}
	<table class="list">
		<thead><tr><th>Titel</th><th class="num">Fragen</th><th class="num">Punkte</th><th class="num">Versuche</th><th></th></tr></thead>
		<tbody>
			{#each exams as exam (exam.id)}
				<tr>
					<td>{exam.title}{#if exam.subject}<small class="muted"> – {exam.subject}</small>{/if}</td>
					<td class="num">{exam.question_count}</td>
					<td class="num">{exam.total_points}</td>
					<td class="num">{exam.attempt_count}</td>
					<td class="row">
						<a class="button" href={`/studium/pruefungen/durchfuehren?exam=${exam.id}&mode=schreiben`}>Schreiben</a>
						<a class="button" href={`/studium/pruefungen/durchfuehren?exam=${exam.id}&mode=abfrage`}>Abfragen</a>
						<button type="button" onclick={() => askDelete(exam)}>Löschen</button>
					</td>
				</tr>
			{:else}
				<tr><td colspan="5">Noch keine Prüfungen.</td></tr>
			{/each}
		</tbody>
	</table>
{/if}

<h3>Neue Prüfung im Stil eines Professors</h3>
{#if loaded && profiles.length === 0}
	<p>Lege zuerst ein <a href="/studium/profile">Prof-Profil</a> an.</p>
{:else}
	<form
		onsubmit={(event) => {
			event.preventDefault();
			generate();
		}}
	>
		<label>
			Profil
			<select bind:value={profileId}>
				<option value="">Bitte wählen</option>
				{#each profiles as profile (profile.id)}
					<option value={profile.id}>{profile.name}{profile.subject ? ` (${profile.subject})` : ''}</option>
				{/each}
			</select>
		</label>
		<label>Fach (leer: aus dem Profil)<input bind:value={subject} maxlength="200" /></label>
		<label>Themen (optional)<input bind:value={topics} maxlength="300" placeholder="z. B. Lagerhaltung, Bestellpunkt" /></label>
		<label>Anzahl Fragen<input type="number" bind:value={count} min="1" max="40" /></label>
		<button type="submit" disabled={busy || profileId === ''}>Entwurf erzeugen</button>
		{#if busy}<small>Der Lern-Coach sucht Altklausuren und Stoff … das kann etwas dauern.</small>{/if}
	</form>
{/if}

{#if draft.length > 0}
	<h3>Entwurf prüfen</h3>
	<p class="muted">Nichts ist gespeichert. Streiche oder ändere Fragen und speichere dann.</p>
	<label>Titel<input bind:value={title} maxlength="200" /></label>
	{#each draft as question, i (i)}
		<fieldset>
			<label class="row">
				<input type="checkbox" bind:checked={question.keep} style="width:auto" />
				Frage {i + 1} übernehmen – {kindLabel[question.kind]}{question.topic ? `, ${question.topic}` : ''}, {question.points} Punkte
			</label>
			<label>Aufgabe<textarea bind:value={question.prompt} rows="3" maxlength="4000" disabled={!question.keep}></textarea></label>
			{#if question.options.length > 0}
				<ul>{#each question.options as option, o (o)}<li>{option}</li>{/each}</ul>
			{/if}
			<label>Musterlösung<textarea bind:value={question.model_answer} rows="3" maxlength="4000" disabled={!question.keep}></textarea></label>
			{#if question.source_citation}<small class="muted">{question.source_citation}</small>{/if}
		</fieldset>
	{/each}
	<button type="button" class="primary" onclick={askSave} disabled={questionsToSave(draft).length === 0 || title.trim() === ''}>
		{questionsToSave(draft).length} Fragen speichern
	</button>
{/if}

<ConfirmDialog
	open={pending !== null}
	title={pending?.title ?? ''}
	message={pending?.message ?? ''}
	confirmLabel={pending?.label ?? ''}
	{onconfirm}
	oncancel={() => (pending = null)}
/>
